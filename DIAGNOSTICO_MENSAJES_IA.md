# Diagnóstico: la IA solo responde cuando tú escribes

## Hallazgo principal
En este repositorio no hay código de backend, workers ni configuración de webhooks/colas para envío proactivo de mensajes.
Con el estado actual, el comportamiento esperado es **reactivo**: la IA responde únicamente tras recibir una entrada del usuario.

## Causas comunes de este síntoma
1. **No existe un proceso programado** (cron/queue worker) que dispare mensajes salientes.
2. **Falta de webhook/evento externo** que active el flujo sin intervención del usuario.
3. **Restricciones del canal** (WhatsApp, Telegram, etc.): muchos proveedores no permiten iniciar conversación libremente.
4. **No hay almacenamiento de contexto/recordatorios** para decidir cuándo enviar mensajes automáticamente.

## Qué implementar para que envíe mensajes sin que escribas primero
1. Un **scheduler** (cron, Celery beat, BullMQ, Temporal, etc.) que evalúe reglas periódicamente.
2. Un **worker de envíos** desacoplado (cola) para mandar mensajes.
3. **Reglas de disparo** (recordatorios, seguimiento, inactividad, eventos de negocio).
4. **Consentimiento del usuario** y cumplimiento de políticas del canal.
5. **Observabilidad** (logs, métricas, reintentos, DLQ) para detectar fallos de entrega.

## Checklist técnico rápido
- [ ] Existe endpoint de salida (API del canal) con credenciales válidas.
- [ ] Hay tarea periódica registrada y ejecutándose en producción.
- [ ] Se guardan destinatarios, ventanas horarias y plantillas.
- [ ] Hay control de rate limits y reintentos exponenciales.
- [ ] Se monitorean errores 4xx/5xx del proveedor.

## Siguiente paso recomendado
Compartir el código del servicio que recibe y envía mensajes (webhook/controlador + worker + configuración de despliegue). Con eso se puede localizar el punto exacto que impide el envío proactivo.
