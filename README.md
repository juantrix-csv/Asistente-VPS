# Clawd Bot + Telegram + Obsidian

Starter para correr OpenClaw como "Clawd Bot", hablarle por Telegram y guardar su memoria/wiki en una carpeta compatible con Obsidian.

## Que arma esto

- Canal Telegram habilitado.
- Acceso por DM con pairing o allowlist por ID numerico de Telegram.
- Plugin `memory-wiki` usando Markdown en modo Obsidian.
- Skill local para que el agente use el vault como notas personales y no pise contenido sin pedir contexto.
- Script PowerShell para instalar OpenClaw, escribir la config y arrancar el gateway.

## Requisitos

- Node.js 24 recomendado, o Node.js 22.14+.
- Token de BotFather para Telegram.
- Una carpeta para el vault de Obsidian. Puede ser un vault dedicado o una carpeta nueva que despues abras desde Obsidian.

## Setup rapido en Windows PowerShell

Desde este repo:

```powershell
.\scripts\setup-openclaw-telegram-obsidian.ps1 `
  -TelegramBotToken "123456:ABC..." `
  -ObsidianVaultPath "C:\Users\juano\Documents\Obsidian\Clawd" `
  -InstallOpenClaw
```

Si ya sabes tu ID numerico de Telegram, agregalo para dejar el bot cerrado solo para vos:

```powershell
.\scripts\setup-openclaw-telegram-obsidian.ps1 `
  -TelegramBotToken "123456:ABC..." `
  -ObsidianVaultPath "C:\Users\juano\Documents\Obsidian\Clawd" `
  -AllowFrom "123456789" `
  -InstallOpenClaw `
  -StartGateway
```

Si no pasas `-AllowFrom`, queda en modo `pairing`: mandale un DM al bot y despues corre:

```powershell
openclaw pairing list telegram
openclaw pairing approve telegram <CODIGO>
```

## Setup rapido en VPS Linux

En el VPS, desde este repo:

```bash
./scripts/setup-openclaw-telegram-obsidian.sh \
  --telegram-bot-token "123456:ABC..." \
  --obsidian-vault-path "/root/obsidian-vault/clawd" \
  --install-openclaw
```

Con allowlist:

```bash
./scripts/setup-openclaw-telegram-obsidian.sh \
  --telegram-bot-token "123456:ABC..." \
  --obsidian-vault-path "/root/obsidian-vault/clawd" \
  --allow-from "123456789" \
  --install-openclaw \
  --start-gateway
```

## Arranque diario

```powershell
openclaw gateway
```

Chequeos utiles:

```powershell
openclaw --version
openclaw doctor
openclaw gateway status
openclaw logs --follow
```

## Obsidian

Abri en Obsidian la carpeta que pusiste en `-ObsidianVaultPath`. El bot va a crear Markdown dentro de ese vault mediante `memory-wiki`.

Para un vault personal existente, conviene empezar con una copia o un vault dedicado. El plugin puede crear archivos de control como `AGENTS.md`, `WIKI.md` y notas auxiliares.

## Config generada

El script escribe `~/.openclaw/openclaw.json` y hace backup si ya existia. La plantilla base esta en:

```text
config/openclaw.telegram-obsidian.template.json
```

La skill que se copia al workspace de OpenClaw esta en:

```text
skills/obsidian-vault/SKILL.md
```

## Fuentes oficiales

- Instalacion OpenClaw: https://docs.openclaw.ai/install
- Canal Telegram: https://docs.openclaw.ai/channels/telegram
- Plugin memory-wiki: https://docs.openclaw.ai/plugins/memory-wiki
