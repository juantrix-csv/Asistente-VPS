# Seguimiento de hábitos de Juan

## Objetivo

Usar los heartbeats para iniciar mensajes proactivos útiles y firmes, sin spam, para ayudar a Juan a cumplir hábitos y tareas.

## Horarios base (UTC)

- 08:10 → recordatorio rutina AM: dientes + skincare.
- 23:00 → activar modo anti recaída, recordar evitar contenido adulto antes de dormir.
- 23:10 → recordatorio rutina PM: dientes + skincare.
- 23:30 → cierre del día: confirmar hábitos y gasto impulsivo.

## Reglas de ejecución

- Si llega un heartbeat y coincide con una ventana activa, revisar `memory/heartbeat-state.json`.
- Si la tarea del bloque horario no está confirmada, enviar mensaje proactivo breve y accionable.
- Si ya fue recordada recientemente, no repetir salvo que corresponda escalar.
- Si Juan confirma cumplimiento, marcar la tarea como completada y resetear el nivel de insistencia.

## Escalado

- Nivel 1: recordatorio breve.
- Nivel 2: si pasan 10-15 min sin confirmación, mensaje más directo.
- Nivel 3: si pasan 20-30 min sin confirmación, intervención concreta con acción mínima inmediata.

## Criterio de silencio

Responder `HEARTBEAT_OK` si:
- no hay tarea activa,
- la tarea ya fue confirmada,
- o el último aviso fue demasiado reciente y todavía no toca escalar.

## Cierre diario

En el bloque de 23:30, pedir estado de:
- dientes PM
- skincare PM
- contenido adulto (limpio o recaída)
- gastos impulsivos del día frente al tope de ARS 10.000
