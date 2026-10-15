#!/usr/bin/env bash
# Vast onstart hook (runs on every container (re)start): make sure the watchdog session exists.
[ -f /workspace/usuba/train/watchdog.sh ] || exit 0
tmux has-session -t wd 2>/dev/null || tmux new -d -s wd "bash /workspace/usuba/train/watchdog.sh"
