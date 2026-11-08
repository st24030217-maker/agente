# WhatsApp de clientes con Kapso

Sebax atiende a los clientes de SSSSolutions en un número de WhatsApp conectado a Kapso.
Tu WhatsApp personal (Baileys) sigue funcionando igual: ahí recibes los avisos y das órdenes.

## Cómo funciona

```
Cliente -> número Kapso -> webhook POST /webhook/kapso (firma verificada)
        -> ¿chat en modo humano?           -> la IA no responde
        -> ¿pide persona / queja / pago?   -> pausa la IA, avisa al cliente y te avisa a ti
        -> resto                           -> respuesta comercial de Sebax (sin herramientas) vía Kapso
```

- Los clientes **nunca** reciben herramientas de administrador (terminal, archivos, campañas).
- Cada mensaje queda registrado como prospecto en el CRM y recibes el aviso de siempre.

## Variables de entorno (en el servidor, nunca en Git)

| Variable | Valor |
| - | - |
| `KAPSO_API_KEY` | API key del proyecto (Kapso > Integrations > API keys) |
| `KAPSO_PHONE_NUMBER_ID` | `597907523413541` (Sandbox) o el ID del número real |
| `KAPSO_WEBHOOK_SECRET` | Secreto que Kapso muestra al crear el webhook |
| `KAPSO_AUTO_REPLY` | `off`, `test` (predeterminado) u `on` |
| `KAPSO_TEST_NUMBERS` | Tus números de prueba, separados por coma |
| `KAPSO_HANDOFF_HOURS` | Horas de silencio tras un traspaso (`0` = hasta `/bot`) |

## Registrar el webhook

Con la URL pública del agente (Render, Railway o Cloudflare Tunnel):

```bash
kapso whatsapp webhooks new \
  --phone-number-id 597907523413541 \
  --url "https://TU-DOMINIO/webhook/kapso" \
  --event whatsapp.message.received \
  --active
```

Copia el secreto que imprime en `KAPSO_WEBHOOK_SECRET` y reinicia el agente.

## Traspaso a humano

Se activa cuando el cliente pide a una persona (o a Sebastián), o habla de quejas,
reembolsos, cancelaciones, facturas, cobros, o dice que algo no funciona o que es urgente.
La lista está en `HANDOFF_KEYWORDS`, dentro de `src/agente/kapso.py`.

Comandos desde tu WhatsApp de dueño:

- `/humano 5218711112222`: Sebax deja de responder a ese cliente.
- `/bot 5218711112222`: Sebax vuelve a responder.
- `/pausados`: lista los chats en modo humano.

Responde a los clientes en pausa desde la bandeja (Inbox) de Kapso.

## Activar para clientes reales

1. Prueba con `KAPSO_AUTO_REPLY=test` y tu número en `KAPSO_TEST_NUMBERS`.
2. Conecta un número real de negocio en Kapso (el Sandbox solo admite números de prueba).
3. Cambia a `KAPSO_AUTO_REPLY=on`.

Estado: `GET /api/kapso/status` (requiere `ADMIN_TOKEN`).
