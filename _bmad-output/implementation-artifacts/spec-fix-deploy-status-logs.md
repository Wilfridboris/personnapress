---
title: 'Fix deploy script: add service status check and log output'
type: 'bugfix'
created: '2026-07-08'
status: 'done'
route: 'one-shot'
---

## Intent

**Problem:** `deploy.sh` restarted the systemd service and immediately declared success with no check — a failed startup produced no error and no logs, leaving the operator blind.

**Approach:** After the restart, poll `systemctl is-active` up to 5 times (3 s apart, 15 s max). On failure, print full `systemctl status` and the last 50 journal lines then exit 1. On success, print the last 20 journal lines for confirmation.

## Suggested Review Order

- [`deploy.sh:26-44`](../../deploy.sh) — polling loop, failure branch (logs + exit 1), success branch (20-line tail)
