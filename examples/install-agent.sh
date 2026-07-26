#!/usr/bin/env bash
# Put a 5am server agent under systemd — the deployment example from
# ../docs/server-agent.md. Background and use cases:
# https://5am.app/blog/server-agents-ask-your-infrastructure
#
# Writes two units (three if you sample something), starts them, and leaves
# the OS to supervise: restart on failure, start at boot, logs in the journal.
# That is the part worth automating — `5am serve agent` is a foreground daemon,
# so started from a shell it dies with the shell and your agent silently goes
# offline.
#
#   sudo AGENT_NAME=web-1 ./install-agent.sh
#
# Everything is configurable by environment; sensible defaults below. Re-running
# is safe — it overwrites the units and restarts.
set -euo pipefail

# ── configure ───────────────────────────────────────────────────────────────
AGENT_NAME="${AGENT_NAME:-$(hostname -s)}"     # name your character will use
RUN_USER="${RUN_USER:-$(id -un)}"              # the user that ran `5am login`

# A log file to follow into a dataset. Leave LOG_FILE empty to skip this unit.
LOG_FILE="${LOG_FILE:-/var/log/nginx/access.log}"
DATASET="${DATASET:-requests}"
SCHEMA="${SCHEMA:-/etc/5am/requests.schema.json}"
LOG_FORMAT="${LOG_FORMAT:-combined}"           # `combined` or `jsonl`

# A command that prints ONE JSON line per run (e.g. examples/sysmetrics.sh).
# Leave SAMPLER empty to skip the timer.
SAMPLER="${SAMPLER:-}"
SAMPLE_DATASET="${SAMPLE_DATASET:-sysmetrics}"
SAMPLE_SCHEMA="${SAMPLE_SCHEMA:-/etc/5am/sysmetrics.schema.json}"
SAMPLE_JSONL="${SAMPLE_JSONL:-/var/log/5am/sysmetrics.jsonl}"
SAMPLE_EVERY="${SAMPLE_EVERY:-60s}"

# ── resolve ─────────────────────────────────────────────────────────────────
[ "$(id -u)" -eq 0 ] || { echo "run me with sudo (I write /etc/systemd/system)" >&2; exit 1; }

# systemd's ExecStart does no $PATH lookup, so every command needs a full path.
# `sudo` also narrows PATH to secure_path, which is why `command -v` can fail
# here for a tool that works fine in your interactive shell.
FIVEAM="${FIVEAM:-$(command -v 5am || true)}"
[ -x "${FIVEAM:-}" ] || { echo "5am not found — set FIVEAM=/full/path/to/5am" >&2; exit 1; }

HOME_DIR="$(getent passwd "$RUN_USER" | cut -d: -f6)"
[ -d "${HOME_DIR:-}" ] || { echo "user $RUN_USER has no home dir (the CLI keeps its token there)" >&2; exit 1; }

# 5AM_* env names begin with a digit, so a shell cannot export or expand them.
# `env NAME=VALUE cmd` is the only way to place them in a child's environment.
KEYRING_OFF='5AM_DISABLE_KEYRING=1'

unit() { printf '%s\n' "$1" > "/etc/systemd/system/$2"; echo "wrote $2"; }

# ── the agent itself ────────────────────────────────────────────────────────
unit "[Unit]
Description=5am server agent ($AGENT_NAME)
After=network-online.target
Wants=network-online.target

[Service]
User=$RUN_USER
Environment=HOME=$HOME_DIR
ExecStart=/usr/bin/env $KEYRING_OFF $FIVEAM serve agent --name $AGENT_NAME
Restart=always
RestartSec=5
NoNewPrivileges=yes

[Install]
WantedBy=multi-user.target" 5am-agent.service

UNITS=(5am-agent.service)

# ── follow a log file into a dataset ────────────────────────────────────────
if [ -n "$LOG_FILE" ]; then
  unit "[Unit]
Description=5am ingest ($DATASET <- $LOG_FILE)
After=network-online.target

[Service]
User=$RUN_USER
Environment=HOME=$HOME_DIR
ExecStart=/usr/bin/env $KEYRING_OFF $FIVEAM data ingest \\
  --dataset $DATASET --schema $SCHEMA \\
  --file $LOG_FILE --format $LOG_FORMAT --follow
Restart=always
RestartSec=5
NoNewPrivileges=yes

[Install]
WantedBy=multi-user.target" 5am-ingest.service
  UNITS+=(5am-ingest.service)
fi

# ── sample a command on a timer ─────────────────────────────────────────────
if [ -n "$SAMPLER" ]; then
  mkdir -p "$(dirname "$SAMPLE_JSONL")"
  touch "$SAMPLE_JSONL"; chown "$RUN_USER" "$SAMPLE_JSONL"

  # sh -c because appending with `>>` is a shell feature, and ExecStart has no
  # shell. Two ExecStart lines run in order: sample, then ingest.
  unit "[Unit]
Description=5am sample + ingest ($SAMPLE_DATASET)

[Service]
Type=oneshot
User=$RUN_USER
Environment=HOME=$HOME_DIR
ExecStart=/bin/sh -c '$SAMPLER >> $SAMPLE_JSONL'
ExecStart=/usr/bin/env $KEYRING_OFF $FIVEAM data ingest \\
  --dataset $SAMPLE_DATASET --schema $SAMPLE_SCHEMA --file $SAMPLE_JSONL" 5am-sample.service

  unit "[Unit]
Description=Run the 5am sampler every $SAMPLE_EVERY

[Timer]
OnBootSec=30s
OnUnitActiveSec=$SAMPLE_EVERY
Unit=5am-sample.service

[Install]
WantedBy=timers.target" 5am-sample.timer
  UNITS+=(5am-sample.timer)
fi

# ── start everything ────────────────────────────────────────────────────────
systemctl daemon-reload
for u in "${UNITS[@]}"; do
  systemctl enable --now "$u" >/dev/null
  echo "started $u"
done

echo
echo "Check it worked:"
echo "  systemctl status ${UNITS[0]}"
echo "  sudo -u $RUN_USER env $KEYRING_OFF $FIVEAM agent list --pretty   # want: online true"
JOURNAL=""; for u in "${UNITS[@]}"; do JOURNAL="$JOURNAL -u $u"; done
echo "  journalctl$JOURNAL -f"
echo
echo "Stop / start / remove:"
echo "  sudo systemctl stop    ${UNITS[*]}"
echo "  sudo systemctl start   ${UNITS[*]}"
echo "  sudo systemctl disable --now ${UNITS[*]}   # and stop starting at boot"
echo
echo "Stopping loses nothing: ingestion resumes from its saved byte offset, so"
echo "log lines that arrive meanwhile are picked up when you start it again."
