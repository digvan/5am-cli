# Server Agent (`5am serve agent`)

Deploy the 5am CLI to your own servers as a lightweight agent, ingest
operational data (access logs, metrics, anything) into a local typed store,
and let your AI Characters answer live questions about it in chat:

> **You:** how many unique IPs hit web-1 in the last 24 hours?
> **Character:** 1,284 unique IPs connected to web-1 since this time yesterday.

The character's `query_server` skill reaches the agent
through the 5am backend; the data itself never leaves your server — the agent
answers structured queries against its local SQLite store and returns only
the result.

For the why — the design constraints, the studio use cases, and what a
character can and cannot run on your machines — see the announcement post:
https://5am.app/blog/server-agents-ask-your-infrastructure

## Architecture — outbound only

```
  Character chat turn (backend)
    └─ skill: query_server(server_name, capability, args)
         └─ enqueues a command row … and awaits ────────────┐
                                                            │
  your server: 5am serve agent --name web-1                 │
    • long-polls GET /api/agents/commands (outbound HTTPS)  │
    • executes locally:                                     │
        – dataset_query over ~/.5am/agent/data.db           │
        – custom skills from ~/.5am/skills/*.json           │
    • POSTs the result back ────────────────────────────────┘
                              → resolves the awaiting turn inline
```

Design properties worth knowing:

- **No inbound port.** The agent only dials out to the API over HTTPS
  (long-poll, ≤25 s per request). It works behind NAT, strict firewalls, and
  corporate proxies; there is no TLS certificate or reverse proxy to manage.
  (Long-poll was chosen over SSE deliberately — SSE through buffering proxies
  is a known failure mode.)
- **Live answers.** A query lands on the agent's already-open poll, executes,
  and resolves back into the *same* chat turn — typically 1–3 s end to end.
  If the agent is offline the character says so immediately instead of
  hanging (the backend fast-fails after 90 s without a poll).
- **Operator-declared execution only.** The agent can run exactly two kinds
  of work: built-in dataset queries, and the custom skills *you* declared as
  manifests. There is no code path by which a character can run arbitrary
  commands — `run_command` and the other chat-loop local skills are
  structurally unreachable in the daemon.
- **Local-first data.** Ingested rows stay in SQLite on your server. Only
  query *results* (counts, top-N buckets) transit the backend, capped at
  32 KB per response.

## Quickstart

```bash
# 1. Authenticate (a READ-ONLY PAT is enough and recommended — the agent
#    endpoints only need read scope, so a token stolen from the server
#    cannot touch your media).
5am login

# 2. Describe your data once, as a typed schema:
cat > requests.schema.json <<'EOF'
{
  "fields": { "ip": "string", "path": "string", "status": "number", "ts": "timestamp" },
  "time_field": "ts"
}
EOF

# 3. Ingest your access log — the combined nginx/apache format is parsed
#    natively (into ip/method/path/status/bytes/ts), no converter needed.
#    --file keeps a resume checkpoint, so re-running only ingests NEW lines:
5am data ingest --dataset requests --schema requests.schema.json \
    --file /var/log/nginx/access.log --format combined

#    Any other source: pipe JSONL (one object per line; unknown keys are
#    ignored, timestamps accept RFC3339 / unix s, ms, µs or ns — unit
#    inferred by magnitude, so journalctl's __REALTIME_TIMESTAMP just works)
#    — write your own converter for custom text formats:
journalctl -o json -u my-app | 5am data ingest --dataset app_journal --schema journal.schema.json

# 4. Sanity-check locally — this is the same query engine characters use:
5am data query --dataset requests --op count_distinct --field ip --since -24h

# 5. Run the agent:
5am serve agent --name web-1

# 6. In the web UI (or via API), enable the "Query Server Agent" skill on a
#    character — then just ask it about your server.
```

`5am agent list` shows your registered agents and whether each is online
(has polled within the last 90 s). `5am agent remove <name>` revokes one.

## What people point it at (studio use cases)

The examples in this doc use an access log because it's universal, but the
sweet spot is the machines behind a media practice:

| machine | wire up | the character can answer |
|---|---|---|
| **Portfolio / gallery server** | access log → `--format combined` (the quickstart) | "how many unique visitors this week?", "which gallery gets the most traffic?" |
| **Studio NAS / archive** | nightly `find … \| jq -Rc` inventory → `--replace` snapshot dataset (path, bytes, mtime) | "how many files landed this month?", "biggest file?" (`stats` max), "when was it last touched?" (`latest`) |
| **Render / edit box** | `examples/sysmetrics.sh` dataset + a `render_queue_depth` custom skill (`ls queue \| wc -l`) | "is the render box free?", "was it maxed overnight?", "anything still queued?" |
| **Card offload / ingest station** (Mac mini, Pi) | have the offload script log a JSON line per file → dataset | "how many files came off the cards last night?", "did the offsite sync finish?" |
| **Backup host** | custom skill wrapping `rclone check` / `rsync --dry-run` for a `{{shoot}}` folder | "is Tuesday's shoot safely offsite?" |
| **Any app server** | a sampler reporting CPU/memory/disk plus your process manager and database | "is the backend healthy right now?", "was the database slow last night?" |

One character sees the whole fleet and routes each question to the right
machine — a single "how big is the Hernandez shoot, and is anything still
rendering?" fans out to `studio-nas` and `render-1` in one turn.

## Datasets

- Store: `~/.5am/agent/data.db` (override the directory with `--data-dir` or
  `$5AM_AGENT_DIR`). SQLite in WAL mode — a cron'd `5am data ingest` and the
  running daemon coexist fine. The directory is created `0700`: ingested
  logs are operator data, and "local-first" includes other local users.
- Schema file: `{"fields": {name: type, …}, "time_field": "<field>"}`.
  Types: `string`, `number`, `timestamp` (stored as unix ms; ingest accepts
  RFC3339 or unix epochs in s/ms/µs/ns, unit inferred by magnitude).
  `time_field` is optional but required for `--since/--until` time-range
  queries. Dataset and field names must match `[a-z][a-z0-9_]{0,63}`.
- Re-ingesting with the same schema appends. `--replace` rebuilds the
  dataset from scratch (drops rows, resets file checkpoints); a changed
  schema errors unless you pass it.
- Bad rows are counted and skipped (`rows_rejected` + first errors in the
  summary) — including lines over the 1 MiB length cap, so a stray binary
  blob in a log can't wedge or bloat the ingester; `--strict` aborts on the
  first bad row instead.
- Retention is yours to manage: `5am data prune --dataset requests
  --keep-days 30` (cron it alongside the ingest).

## Automated ingestion

`--file` is what makes ingestion automatable: the store keeps a byte-offset
checkpoint per (dataset, file) — committed in the same transaction as the
rows — so every run consumes exactly the lines that arrived since the last
one. Log rotation (new inode) and truncation (copytruncate) are detected and
restart the file from the top; a half-written trailing line is left for the
next pass. A naive `cat log | 5am data ingest` cron job re-ingests the whole
file every run and duplicates everything — always use `--file` for files.

Two deployment shapes:

1. **Continuous (`--follow`, recommended)** — one long-running process with
   `tail -F` semantics, run as a second systemd unit next to the agent:

   ```bash
   # The ExecStart body for a systemd unit (the full unit is in the
   # "Deployment walkthrough" below, Step 4) — not a command to run by hand.
   # Do NOT append `&`: this blocks like `tail -F`, which is exactly what
   # systemd's default Type=simple wants, and ExecStart runs no shell, so an
   # `&` would be passed to the CLI as a literal argument.
   5am data ingest --dataset requests --schema /etc/5am/requests.schema.json \
       --file /var/log/nginx/access.log --format combined --follow
   ```

   New lines are queryable within ~1 s. On SIGTERM it flushes and
   checkpoints, so restarts lose nothing.

   Running it by hand to try it out is fine — it just blocks. Detach with
   `nohup … &` rather than a bare `&`: only SIGINT and SIGTERM trigger the
   clean flush, so closing the terminal (SIGHUP) kills it mid-batch. That is
   harmless — the checkpoint commits in the same transaction as the rows, so
   the next run simply re-reads the uncommitted lines — but it is why the
   systemd unit is the shape worth deploying.

2. **Periodic (cron)** — the same command *without* `--follow` exits after
   catching up; schedule it as often as you want your data fresh:

   ```cron
   * * * * * fiveam /usr/local/bin/5am data ingest --dataset requests \
       --schema /etc/5am/requests.schema.json \
       --file /var/log/nginx/access.log --format combined
   ```

Formats: `--format combined` covers nginx/apache access logs natively. For
anything else, emit JSONL: nginx can log JSON directly (a `log_format json_combined escape=json …` block gives you custom fields with no converter at
all), `journalctl -o json` already is JSONL, and custom text formats go
through whatever converter you like piped into stdin (stdin has no
checkpoint, so prefer file-based sources for anything scheduled).

### Example: any script → dataset (system metrics)

Access logs are just one source — anything that can print a JSON line per
sample becomes a queryable dataset. The bundled
[`examples/sysmetrics.sh`](../examples/sysmetrics.sh) (Linux + macOS) emits one
CPU/memory/disk/load sample:

```json
{"cpu_pct":18.3,"mem_pct":71.2,"disk_pct":64,"load1":2.41,"ts":"2026-07-22T10:15:00Z"}
```

Wire it up on the server:

```bash
# /etc/5am/sysmetrics.schema.json
{ "fields": { "cpu_pct": "number", "mem_pct": "number",
              "disk_pct": "number", "load1": "number", "ts": "timestamp" },
  "time_field": "ts" }
```

```cron
# /etc/cron.d/5am-sysmetrics — sample every minute, ingest incrementally
* * * * * fiveam /usr/local/bin/sysmetrics.sh >> /var/log/5am/sysmetrics.jsonl
* * * * * fiveam /usr/local/bin/5am data ingest --dataset sysmetrics \
    --schema /etc/5am/sysmetrics.schema.json --file /var/log/5am/sysmetrics.jsonl
# weekly retention
0 4 * * 0 fiveam /usr/local/bin/5am data prune --dataset sysmetrics --keep-days 30
```

(Or skip the second cron line and run the ingest under systemd with
`--follow`, exactly like the access-log unit above — one follower per file.)

The same shape extends as far as you want to take it. A sampler for an
application server might add process-manager state (how many workers are
online, errored, restarted) and database health (reachable, query latency,
connection count, size) to the same JSON line — the schema just grows. Make
the failures *data* rather than errors: a database you cannot reach should
emit `db_up: 0`, not abort the sample, so the outage is recorded instead of
leaving a gap where the history should be.

The running agent advertises the dataset automatically (within ~10 min, or
on restart), and the character can then answer:

- *"what's the current memory usage on web-1?"* → `latest`
- *"what was peak CPU there overnight?"* → `stats` on `cpu_pct` with `since`
- *"how many minutes was CPU above 90% this week?"* → `count` with a
  `cpu_pct gte 90` filter and `since: -7d`
- *"when did it last spike?"* → `latest` with the same filter

### Query operations (what a character can ask)

| op | meaning |
|---|---|
| `list_datasets` | datasets with schemas, row counts, covered time range |
| `count` | row count (with optional filters / time range) |
| `count_distinct` | distinct values of `field` |
| `group_by` | top buckets of `field` by count (default 20, max 100) |
| `stats` | min / max / avg of a number `field` (metrics: "peak CPU overnight?") |
| `latest` | the most recent row by the time field ("disk usage right now?") |

Filters: `[{field, op, value}]` with ops `eq ne gt gte lt lte contains`,
ANDed, always parameter-bound. `since`/`until` accept RFC3339 or relative
(`-24h`, `-7d`). All ops compose with filters and time ranges — `latest`
with `cpu_pct gte 90` is "when did CPU last spike?".

## Custom skills as agent capabilities

Every *enabled* manifest in `~/.5am/skills/*.json` (see `5am skills` and the
Custom Skills section of the CLI README) is advertised to the backend as an
agent capability — name, description, and input schema **only**; the command
line itself never leaves the server. A character invokes one by name and
passes its arguments as a JSON string (`custom_args_json`), which only the
agent parses.

Headless destructive policy: the interactive confirm prompt that `5am
characters chat` uses does not exist in a daemon. An invocation whose
expanded command trips the destructive heuristics (rm, dd, kill, …) is
**refused** with `destructive_refused` unless you started the daemon with
`--allow-destructive`.

## Deployment walkthrough (Ubuntu/Debian)

End to end on a fresh server: the agent daemon, an nginx access-log follower,
and backend health both as history and as a live check. Same pattern as the
Camera-to-Cloud runbook. Adapt paths for other distros; nothing here is Debian-specific except `adm` group membership and
`/etc/cron.d` syntax.

> **Prefer a script?** [`examples/install-agent.sh`](../examples/install-agent.sh)
> is a generic, copy-and-adapt installer: it writes the agent unit, an optional
> `--follow` ingest unit for a log file, and an optional sampler timer, then
> starts them. ~80 lines, no 5AM-backend assumptions — point it at your own log
> and sampler.
>
> ```bash
> sudo AGENT_NAME=web-1 ./install-agent.sh                       # agent + nginx log
> sudo AGENT_NAME=web-1 LOG_FILE= ./install-agent.sh             # agent only
> sudo AGENT_NAME=web-1 SAMPLER=/usr/local/bin/sysmetrics.sh \
>      ./install-agent.sh                                        # ...plus a timer
> ```
>
### Step 1 — a service user with a real home directory

```bash
sudo useradd --system --create-home --home-dir /var/lib/fiveam \
     --shell /usr/sbin/nologin fiveam
```

`--create-home` is not optional. The agent stores datasets in `~/.5am/agent`
and reads custom-skill manifests from `~/.5am/skills`; a system user without a
home resolves `~` to `/`, and both silently do nothing. (The alternative is to
set `5AM_AGENT_DIR` and `5AM_SKILLS_DIR` explicitly in the env file below and
skip the home directory entirely.)

### Step 2 — install the CLI

Install per the CLI README (`curl -fsSL https://cli.5am.app/cli/latest/install.sh | sh`),
then make sure the binary is at an absolute path — the systemd units below use
`/usr/local/bin/5am`, because `ExecStart=` has no `$PATH` lookup:

```bash
5am --version
which 5am          # must match the ExecStart paths below
```

### Step 3 — mint a READ-ONLY token

In the web UI: **Settings → CLI tokens → New token**, scope **read**. Every
`/api/agents/*` endpoint needs only `read`, so a token stolen off this server
cannot touch your media.

`/etc/5am/agent.env` — mode `640`, owned `root:fiveam`:

```bash
sudo install -d -m 755 /etc/5am
sudo tee /etc/5am/agent.env >/dev/null <<'EOF'
5AM_TOKEN=5am_pat_replace_me
5AM_DISABLE_KEYRING=1
# Only for a non-default backend:
# 5AM_BASE_URL=https://5am.app
EOF
sudo chown root:fiveam /etc/5am/agent.env
sudo chmod 640 /etc/5am/agent.env
```

`5AM_DISABLE_KEYRING=1` matters on a headless box: without it the CLI tries an
OS keychain that isn't there and falls back with a warning on every run.

### Step 4 — nginx access log → `requests` dataset

**4a. Let the agent read the log.** On Debian/Ubuntu `/var/log/nginx` is
`root:adm`:

```bash
sudo usermod -aG adm fiveam
sudo -u fiveam head -1 /var/log/nginx/access.log   # must print a line
```

**4b. Write the schema.** The `combined` parser produces exactly these fields:

```bash
sudo tee /etc/5am/requests.schema.json >/dev/null <<'EOF'
{
  "fields": {
    "ip": "string", "method": "string", "path": "string",
    "status": "number", "bytes": "number", "ts": "timestamp"
  },
  "time_field": "ts"
}
EOF
```

**4c. Prove it works before making it a service.** Run one catch-up pass by
hand as the agent user and query it locally:

```bash
sudo -u fiveam /usr/local/bin/5am data ingest --dataset requests \
    --schema /etc/5am/requests.schema.json \
    --file /var/log/nginx/access.log --format combined

sudo -u fiveam /usr/local/bin/5am data query \
    --dataset requests --op count_distinct --field ip --since -24h
```

The ingest prints `rows_ingested` / `rows_rejected`. A high reject count means
the log isn't `combined` format — check `rows_rejected` and the first errors in
the summary before going further.

**4d. Make it continuous.** `/etc/systemd/system/5am-agent-ingest.service`:

```ini
[Unit]
Description=5AM agent ingest (nginx access log)
After=network-online.target

[Service]
User=fiveam
EnvironmentFile=/etc/5am/agent.env
ExecStart=/usr/local/bin/5am data ingest --dataset requests \
  --schema /etc/5am/requests.schema.json \
  --file /var/log/nginx/access.log --format combined --follow
Restart=always
RestartSec=5
NoNewPrivileges=yes

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now 5am-agent-ingest
systemctl status 5am-agent-ingest      # want: active (running)
```

One follower per file. Log rotation is handled — a new inode restarts the file
from the top, and the byte-offset checkpoint means nothing is double-counted.

### Step 5 — run the agent

`/etc/systemd/system/5am-agent.service`:

```ini
[Unit]
Description=5AM server agent (web-1)
After=network-online.target
Wants=network-online.target

[Service]
User=fiveam
EnvironmentFile=/etc/5am/agent.env
ExecStart=/usr/local/bin/5am serve agent --name web-1
Restart=always
RestartSec=5
NoNewPrivileges=yes

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now 5am-agent
journalctl -u 5am-agent -f
```

### Step 6 — verify end to end

```bash
# 1. Both units up
systemctl is-active 5am-agent 5am-agent-ingest        # active, active

# 2. The account sees the agent as ONLINE (it polled within the last 90 s).
#    This is the check worth doing — an agent that registered once and then
#    stopped shows up here as online:false, and the character will correctly
#    report the machine as unreachable.
5am agent list --pretty

# 3. The dataset has rows, read from the agent's own local store
sudo -u fiveam /usr/local/bin/5am data query --op list_datasets --pretty
sudo -u fiveam /usr/local/bin/5am data query --dataset requests \
    --op count_distinct --field ip --since -24h
```

Then in the web UI enable the **Query Server Agent** skill on a character and
ask it something you can check by hand:

- *"how many unique IPs hit web-1 in the last 24 hours?"* → should match the
  number Step 4c printed
- *"which paths get the most traffic?"* → `group_by` over `path`
- *"any 500s today?"* → `count` with a `status gte 500` filter

A new dataset is advertised on agent startup and every 10 minutes after, so if
the character can't see one you just created, restart `5am-agent` rather than
waiting.

## Security model

- **Auth**: the agent uses a normal user PAT; every `/api/agents/*` endpoint
  requires only `read` scope *by design*, so mint the PAT read-only.
  Character-bound tokens are rejected on these endpoints. If a server is
  ever compromised, **revoke its PAT** (Settings → CLI tokens) — `5am agent
  remove` only unregisters the name, and whoever holds the token could
  simply re-register.
- **Execution surface**: `{dataset_query} ∪ your enabled manifests`. Nothing
  else dispatches. Capability advertisements never include `run`/`shell`/env
  (enforced agent-side AND re-validated by the backend).
- **Caps**: results are truncated at 32 KB (agent AND backend), commands
  expire after 60 s, at most 8 commands may be in flight per agent, and the
  character-facing skill truncates further to 8 KB.
- **Injection**: dataset/field identifiers are regex-validated against the
  stored schema, operators are enum-mapped, values are bound parameters — a
  model-authored string never becomes SQL text.
- **Audit**: every `query_server` invocation is written to
  `character_skill_invocations` (mode, server, sizes — never your data).

## Troubleshooting

| symptom | check |
|---|---|
| character says the agent is offline | `5am agent list` — `online` flips ~90 s after the daemon stops polling; `journalctl -u 5am-agent` |
| `unknown_agent` in the daemon log | the name was revoked (`5am agent remove`) — the daemon re-registers automatically within seconds |
| `agent_timeout` answers | command took >45 s: slow custom skill, or the box is swamped; dataset queries should be ms |
| `destructive_refused` | expected: start the daemon with `--allow-destructive` if you really want that skill callable headlessly |
| `destructive_refused` on a harmless skill | the heuristic screens argument VALUES too — an arg that contains a deny token (a path with `rm` in it, a message mentioning `kill`) trips it. Rename the input or start with `--allow-destructive` |
| character can't see a new dataset | capabilities refresh on registration (startup + every 10 min) — restart the daemon to advertise immediately |
| `409 command_not_claimable` in the log | benign: the command expired while executing, or a duplicate daemon with the same name answered first |

## Backend maintenance windows — what to expect

A short backend outage (e.g. a 5-minute maintenance restart) cannot corrupt,
stick, or double-execute anything — the timeouts, sweeps, and backoffs were
designed for it. What actually happens:

**At the moment the backend goes down**

- A chat turn in flight errors out client-side and is simply re-sent after
  restart (interactions are recorded only on completion — no partial state).
- An in-flight `query_server` command splits into two safe halves: the
  awaiting promise (`agentCommandPendingRegistry`) is in-memory and dies with
  the process — deliberately, so no persisted waiter can go stale; the
  durable `agent_commands` row can no longer be resolved — past its TTL it
  is unclaimable and stops counting toward the in-flight cap immediately
  (both checks compare `expires_at` directly), and the worker sweep stamps
  it `expired` within ~10 minutes. If the agent had already claimed it, it
  executes (read-only, harmless), fails the result POST, logs, and drops —
  no retry by design. Double execution is impossible: a command is never
  re-dispatched once its delivery was ATTEMPTED — the one exception to the
  one-way `pending → running` claim is a poll whose socket died while the
  claim was in flight, where the backend flips the (provably undelivered —
  nothing was written) rows straight back to `pending` for the next poll.

**During the outage**

- The daemon rides its backoff ramp (1→2→5→10→30→60 s, capped) on failed
  polls; it doesn't crash and its JWT survives the restart.
- **Ingestion is completely unaffected** — `data ingest --follow` talks only
  to the local SQLite store. Zero data loss through the window.

**After restart — the one visible wrinkle**

The daemon may be sitting at the top of its 60 s backoff, so its first
post-restart poll (which is also its heartbeat) can land up to a minute
later. Until then `last_seen_at` is stale beyond the 90 s online window, so
the character reports `agent_offline` for a question asked in that gap —
a false negative that self-heals on the next poll. The do-not-fabricate
framing means the character says exactly that rather than inventing data.

Possible future polish (not correctness fixes): a shorter backoff cap for
connection-refused errors specifically, and a graceful SIGTERM drain that
204s held long-polls so daemons cycle immediately.