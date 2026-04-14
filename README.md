# Proactive Messaging (implementación base)

Este repositorio incluye una implementación mínima para que la IA pueda enviar mensajes **sin esperar** a que el usuario escriba primero.

## Componentes
- `Scheduler`: toma recordatorios vencidos y los mueve a `outbox`.
- `Worker`: consume `outbox` y envía mensajes.
- `Store` (SQLite): persiste recordatorios, cola de salida y estados.
- Canales:
  - `stdout` (debug local)
  - `telegram` (Bot API real)
- `TelegramAssistantLoop`: atiende mensajes entrantes y siempre manda un mensaje final de resultado/error.

Archivo principal: `proactive_messaging.py`.

## Qué pasaba con "me pongo con eso" y después silencio
Faltaba un loop de entrada/salida que:
1. reciba el mensaje de Telegram,
2. confirme recepción,
3. procese la tarea,
4. envíe **siempre** un mensaje final (éxito o error).

Ahora eso lo hace `run-telegram-assistant`.

## Uso rápido (local)
```bash
python proactive_messaging.py --db proactive_messages.db init-db
python proactive_messaging.py --db proactive_messages.db add-reminder --user u123 --text "Recordatorio" --at "2026-04-14T12:00:00+00:00"
python proactive_messaging.py --db proactive_messages.db run-scheduler-once
python proactive_messaging.py --db proactive_messages.db run-worker-once
```

## Dejarlo andando por Telegram
> Requisito: el usuario debe iniciar chat con tu bot al menos una vez.

1. Crea bot con `@BotFather` y copia el token.
2. Obtén tu `chat_id` (por ejemplo con `getUpdates` de Telegram Bot API).
3. Exporta token:
```bash
export TELEGRAM_BOT_TOKEN="<tu_token>"
export ASSISTANT_WORKDIR="/opt/Asistente-VPS"
```
4. Inicializa DB y agrega recordatorio usando `chat_id` como `--user`:
```bash
python proactive_messaging.py --db proactive_messages.db init-db
python proactive_messaging.py --db proactive_messages.db add-reminder --user "<chat_id>" --text "Hola desde bot" --at "2026-04-14T12:00:00+00:00"
```
5. Ejecuta procesos (idealmente en 2 o 3 procesos/servicios separados):
```bash
python proactive_messaging.py --db proactive_messages.db run-scheduler --interval 10
python proactive_messaging.py --db proactive_messages.db --channel telegram run-worker --interval 5
python proactive_messaging.py --telegram-token "$TELEGRAM_BOT_TOKEN" run-telegram-assistant --poll-timeout 30 --command-timeout 120 --workdir "$ASSISTANT_WORKDIR"
```

### Comandos por chat
- `estado` muestra rama y cambios locales del repo.
- `pull` ejecuta `git pull --ff-only` en la carpeta del repo.
- `test` ejecuta `python -m pytest -q`.
- `version` muestra el ultimo commit.
- `ayuda` muestra comandos disponibles.
- `/run <comando>` ejecuta un comando shell puntual en la carpeta del repo.

Para probar desde Telegram, manda estos mensajes al bot:

```text
estado
version
pull
test
```

## Test
```bash
python -m pytest -q
```

## Pull automatico en el VPS cuando se pushea a main
El workflow `.github/workflows/vps-pull-on-push.yml` se ejecuta cada vez que se hace push a `main`.
Entra por SSH al VPS, se mueve a la rama `main` y ejecuta `git pull --ff-only origin main`.

Configura estos secretos en GitHub: `Settings > Secrets and variables > Actions`.

- `VPS_SSH_HOST`: host o IP del VPS.
- `VPS_SSH_USER`: usuario SSH.
- `VPS_SSH_PRIVATE_KEY`: clave privada SSH con acceso al VPS.
- `VPS_REPO_PATH`: ruta absoluta del repo en el VPS, por ejemplo `/opt/Asistente-VPS`.
- `VPS_SSH_PORT`: opcional, puerto SSH. Si no existe usa `22`.
- `VPS_SSH_KNOWN_HOSTS`: opcional, salida de `ssh-keyscan -p <puerto> <host>`.
- `VPS_AFTER_PULL_COMMAND`: opcional, comando para ejecutar despues del pull. Sirve para reiniciar el bot, por ejemplo `sudo systemctl restart asistente-vps-telegram`.

Requisitos en el VPS:

- El repo ya debe existir en `VPS_REPO_PATH`.
- El usuario SSH debe tener permisos sobre ese directorio.
- El remoto `origin` debe poder hacer `git fetch` desde GitHub.
- El directorio debe estar limpio; si hay cambios locales sin commit, el workflow falla para no pisarlos.
- Si queres que el bot tome los cambios sin reinicio manual, configura `VPS_AFTER_PULL_COMMAND` con el comando que reinicia el proceso del bot.
