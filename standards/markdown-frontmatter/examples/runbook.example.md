---
schema_version: '1.1'
id: 'runbook-0f943i-restart-netbox-after-config-change'
title: 'Restart netbox after config change'
description: 'Procedure to safely reload netbox after editing its configuration.'
doc_type: 'runbook'
status: 'active'
created: '2026-03-10'
updated: '2026-06-06'
reviewed: '2026-06-02'
owner: 'platform-team'
consumer: 'user'
tags:
  - 'netbox'
  - 'restart'
aliases:
  - 'netbox-restart'
related:
  - 'docs/decisions/adr-0001-homelab-use-postgresql-for-persistent-storage.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
project:
  service: 'netbox'
  environment: 'home-lab'
---

# Restart netbox after config change

## Trigger

Use this runbook after editing `/opt/netbox/netbox/configuration.py` or any file under `/opt/netbox/netbox/` that requires a gunicorn/worker reload (e.g. custom scripts, plugins).

Also triggered by: config management runs that report a changed `configuration.py`.

## Prerequisites

- SSH access to the netbox LXC container (CT 105 on Hetzner, alias `htz-netbox`).
- Confirm no active background jobs in Admin → Jobs before restarting.

## Steps

1. SSH into the container:

   ```bash
   ssh htz-netbox
   ```

2. Check for running background jobs:

   ```bash
   sudo systemctl status netbox-rq
   ```

   If jobs are running, wait for them to finish or note which ones to re-queue after restart.

3. Restart the gunicorn workers:

   ```bash
   sudo systemctl restart netbox
   ```

4. Restart the RQ background worker:

   ```bash
   sudo systemctl restart netbox-rq
   ```

## Verification

```bash
sudo systemctl status netbox netbox-rq
curl -sf http://localhost:8001/api/ | python3 -m json.tool | head -5
```

Both services should show `active (running)`. The `curl` should return a JSON API root.

## Rollback

If netbox fails to start, check the gunicorn log for the error:

```bash
sudo journalctl -u netbox -n 50
```

Common causes: syntax error in `configuration.py`, missing plugin package. Revert the config change and restart again.

## References

- [Netbox administration docs](https://docs.netbox.dev/en/stable/administration/)
