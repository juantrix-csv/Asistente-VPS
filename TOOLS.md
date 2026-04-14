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
