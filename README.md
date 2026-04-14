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
python proactive_messaging.py --telegram-token "$TELEGRAM_BOT_TOKEN" run-telegram-assistant --poll-timeout 30 --command-timeout 120
```

### Comandos por chat
- `/run <comando>` ejecuta comando shell y devuelve salida + código de salida.
- Cualquier otro texto devuelve ayuda y confirmación de cierre de tarea.

## Test
```bash
python -m pytest -q
```
