# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

### VPS Admin

- Primary VPS: local machine, running as `root`.
- Main OpenClaw workspace: `/root/.openclaw/workspace`.
- GitHub repo checkout used for workflow tests: `/root/Asistente-VPS`.
- OpenClaw user service: `openclaw-gateway.service`; manage with `systemctl --user status|restart openclaw-gateway.service`.
- The user wants this agent to administer the VPS from Telegram: inspect services, edit configs, manage repos, run package managers, restart services, and diagnose failures directly when asked.
- Exec policy is intentionally set to full gateway execution with ask off. Still avoid irreversible destructive operations unless the user clearly asks.

### Production Fletes Guardrail

- Production Fletes app path: `/opt/fletes-ostrit`.
- Related production files: `/etc/fletes-ostrit.env`, `/etc/systemd/system/fletes-ostrit-*`, `/etc/nginx/sites-available/fletes-ostrit`, `/etc/nginx/sites-enabled/fletes-ostrit`, `/usr/local/bin/fletes-ostrit-db-backup.sh`.
- Do not edit, delete, move, chmod, chown, install into, rebuild, deploy, reset, pull, checkout, or otherwise modify Fletes production files unless Juan explicitly asks for Fletes work in that message.
- Read-only inspection is allowed when diagnosing general VPS health: `systemctl status`, `journalctl`, `curl` health checks, process lists, and read-only file views.
- OpenClaw is also systemd-sandboxed with these Fletes paths mounted read-only inside `openclaw-gateway.service`.

### Mercado Pago Finance

- Read-only helper command: `lux-mp`.
- Script path: `/root/.openclaw/workspace/tools/mercadopago_finance.py`.
- Credential file: `/root/.config/lux/secrets/mercadopago.env` with `MP_ACCESS_TOKEN=...` and permissions `600`.
- Never print, send, log, or reveal the Mercado Pago access token.
- Use `lux-mp whoami` to validate the token without exposing it.
- Use `lux-mp payments --days 7`, `lux-mp payments --from YYYY-MM-DD --to YYYY-MM-DD`, or `lux-mp payments --format json` to inspect income from payments, fees, refunds, and net received.
- Treat Mercado Pago data as sensitive financial information. Summarize amounts and trends unless Juan asks for transaction-level details.
- Current helper is payment-centric. It does not yet cover every account cash movement such as withdrawals, external transfers, or full settlement exports.

### Fletes Finance API

- Read-only helper command: `lux-finance`.
- Script path: `/root/.openclaw/workspace/tools/fletes_finance.py`.
- Credential file: `/root/.config/lux/secrets/finance-api.env` with `FINANCE_READ_API_KEY=...` and permissions `600`.
- Base URL is read from `FINANCE_API_BASE_URL` or `MAIN_API_BASE_URL`; production currently works locally as `http://127.0.0.1/api/v1`.
- Never print, send, log, or reveal the finance API token.
- Use `lux-finance check` to validate access without exposing the token.
- Use `lux-finance summary`, `lux-finance snapshot`, `lux-finance jobs --from YYYY-MM-DD --to YYYY-MM-DD --status DONE`, `lux-finance drivers`, `lux-finance vehicles`, `lux-finance leads`, or `lux-finance settings` for read-only business finance data.
- Do not call these endpoints with raw `curl` unless you explicitly add the auth header from the local secret; prefer `lux-finance` so the header is always included.
