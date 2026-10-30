import logging
import httpx
from agente.config import settings

logger = logging.getLogger(__name__)

def send_whatsapp_message(to_number: str, message: str) -> str:
    """Envía un mensaje de texto por WhatsApp a un número o a ti mismo.
    Usa prioritariamente Baileys y reporta entrega solo con acuse de WhatsApp.
    
    Args:
        to_number: Número de teléfono con código de país (ej. '5218719164677'). Si se deja vacío o 'self', se envía a ti mismo.
        message: El texto que deseas enviar.
    """
    meta_error = None
    bridge_error = None

    # 1. Modo Puente Baileys (Prioritario si está conectado activamente en status: open)
    try:
        bridge_status_url = f"http://127.0.0.1:{settings.bridge_port}/status"
        with httpx.Client(timeout=3.0) as client:
            st = client.get(bridge_status_url)
            if st.status_code == 200 and st.json().get("status") == "open":
                bridge_url = f"http://127.0.0.1:{settings.bridge_port}/send"
                target = "" if to_number.lower() in ["self", "yo", "mismo", ""] else to_number
                payload = {
                    "to": target,
                    "text": message
                }
                resp = client.post(bridge_url, json=payload, timeout=20.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("delivered") is True:
                        return f"Entrega confirmada por WhatsApp a {data.get('jid', target)} (estado: {data.get('delivery_status', 'confirmado')})."
                    if data.get("accepted") is True:
                        if data.get("delivery_status") == "error":
                            return f"WhatsApp reportó un error de entrega para {data.get('jid', target)} (id: {data.get('message_id') or 'desconocido'})."
                        return (
                            f"Aceptado por el puente para {data.get('jid', target)}, "
                            f"pero entrega no confirmada (estado: {data.get('delivery_status', 'desconocido')}, "
                            f"id: {data.get('message_id') or 'desconocido'})."
                        )
                    bridge_error = "El puente respondió sin confirmar la aceptación ni la entrega."
                else:
                    bridge_error = f"Error Baileys ({resp.status_code}): {resp.text}"
    except Exception as e:
        bridge_error = f"Baileys no disponible: {str(e)}"

    # 2. Modo Meta WhatsApp Business Cloud API Oficial (Fallback o modo Cloud)
    if settings.meta_wa_token and settings.meta_wa_phone_number_id:
        target = to_number.strip()
        if target.lower() in ["self", "yo", "mismo", ""]:
            target = settings.allowed_numbers[0] if settings.allowed_numbers else ""
        
        clean_target = "".join(filter(str.isdigit, target))
        if clean_target.startswith("521") and len(clean_target) == 13:
            clean_target = "52" + clean_target[3:]
        elif len(clean_target) == 10:
            clean_target = "52" + clean_target
        if clean_target:
            headers = {
                "Authorization": f"Bearer {settings.meta_wa_token}",
                "Content-Type": "application/json"
            }
            url = f"https://graph.facebook.com/v19.0/{settings.meta_wa_phone_number_id}/messages"
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": clean_target,
                "type": "text",
                "text": {"preview_url": True, "body": message}
            }
            try:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code in [200, 201]:
                        return f"Aceptado por Meta para +{clean_target}; entrega no confirmada."
                    meta_error = f"Error Meta API ({resp.status_code}): {resp.text}"
            except Exception as e:
                meta_error = f"Error al comunicar con Meta WhatsApp Cloud API: {str(e)}"

    if bridge_error and meta_error:
        return f"Fallo al enviar mensaje: {bridge_error} | {meta_error}"
    return bridge_error or meta_error or "No se pudo enviar el mensaje (canales no disponibles)."


def is_delivery_confirmed(result: str) -> bool:
    return result.startswith("Entrega confirmada por WhatsApp")


def is_delivery_pending(result: str) -> bool:
    return result.startswith(("Aceptado por el puente", "Aceptado por Meta"))
