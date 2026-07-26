#!/bin/sh
# Emit ONE system-metrics sample as a JSON line — the generic-ingest example
# from ../docs/server-agent.md. Append its output to a JSONL file on a
# schedule and let `5am data ingest --file … --follow` (or a cron'd one-shot)
# stream it into a dataset your AI characters can query.
#
#   */1 * * * *  /usr/local/bin/sysmetrics.sh >> /var/log/5am/sysmetrics.jsonl
#
# Fields match sysmetrics.schema.json (shipped beside this script):
#   { "fields": { "cpu_pct": "number", "mem_pct": "number",
#                 "disk_pct": "number", "load1": "number",
#                 "ts": "timestamp" },
#     "time_field": "ts" }
#
# Works on Linux and macOS. Swap in anything you like — the only contract is
# one JSON object per line with types matching the schema.
set -eu

# awk's printf %.1f follows the locale decimal separator — force '.' or the
# emitted JSON is invalid under e.g. LC_NUMERIC=de_DE.
LC_ALL=C
export LC_ALL

ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
disk_pct=$(df -P / | awk 'NR==2 { sub(/%/, "", $5); print $5 }')

case "$(uname -s)" in
  Darwin)
    # Two top samples ~1s apart; the first reports since-boot averages.
    cpu_pct=$(top -l 2 -n 0 | awk -F'[:,]' '/CPU usage/ { idle = $4 } END { gsub(/[% a-z]/, "", idle); printf "%.1f", 100 - idle }')
    mem_pct=$(vm_stat | awk '
      /Pages free/                { free   = $3 }
      /Pages active/              { active = $3 }
      /Pages inactive/            { inact  = $3 }
      /Pages speculative/         { spec   = $3 }
      /Pages wired/               { wired  = $4 }
      /occupied by compressor/    { comp   = $5 }
      END {
        gsub(/\./, "", free); gsub(/\./, "", active); gsub(/\./, "", inact)
        gsub(/\./, "", spec); gsub(/\./, "", wired); gsub(/\./, "", comp)
        total = free + active + inact + spec + wired + comp
        printf "%.1f", (active + wired + comp) / total * 100
      }')
    load1=$(sysctl -n vm.loadavg | awk '{ print $2 }')
    ;;
  *)
    # Linux: vmstat's second sample is the live one; $15 is idle%.
    cpu_pct=$(vmstat 1 2 | awk 'END { print 100 - $15 }')
    mem_pct=$(free | awk '/^Mem:/ { printf "%.1f", ($2 - $7) / $2 * 100 }')
    load1=$(awk '{ print $1 }' /proc/loadavg)
    ;;
esac

printf '{"cpu_pct":%s,"mem_pct":%s,"disk_pct":%s,"load1":%s,"ts":"%s"}\n' \
  "$cpu_pct" "$mem_pct" "$disk_pct" "$load1" "$ts"
