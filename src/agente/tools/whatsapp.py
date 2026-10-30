import logging
import httpx
from agente.config import settings

logger = logging.getLogger(__name__)

def send_whatsapp_message(to_number: str, message: str) -> str:
    """Envía un mensaje de texto por WhatsApp a un número o a ti mismo.
    Soporta tanto Meta WhatsApp Cloud API Oficial como el puente Baileys con fallback automático.
    
    Args:
        to_number: Número de teléfono con código de país (ej. '5218719164677'). Si se deja vacío o 'self', se envía a ti mismo.
        message: El texto que deseas enviar.
    """
    meta_error = None

    # 1. Modo Meta WhatsApp Business Cloud API Oficial
    if settings.meta_wa_token and settings.meta_wa_phone_number_id:
        target = to_number.strip()
        if target.lower() in ["self", "yo", "mismo", ""]:
            target = settings.allowed_numbers[0] if settings.allowed_numbers else ""
        
        clean_target = "".join(filter(str.isdigit, target))
        # Normalización para números celulares de México en Meta Cloud API (remover el '1' después de 52)
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
                        return f"Mensaje enviado con éxito vía Meta WhatsApp Cloud API a +{clean_target}."
                    meta_error = f"Error Meta API ({resp.status_code}): {resp.text}"
                    logger.warning("Fallo Meta WhatsApp Cloud API: %s. Intentando respaldo Baileys...", meta_error)
            except Exception as e:
                meta_error = f"Error al comunicar con Meta WhatsApp Cloud API: {str(e)}"
                logger.warning("Excepción en Meta WhatsApp Cloud API: %s. Intentando respaldo Baileys...", meta_error)

    # 2. Modo Puente Baileys Local (o Fallback automático si Meta falla)
    try:
        bridge_url = f"http://127.0.0.1:{settings.bridge_port}/send"
        target = "" if to_number.lower() in ["self", "yo", "mismo", ""] else to_number
        payload = {
            "to": target,
            "text": message
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(bridge_url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return f"Mensaje enviado con éxito por WhatsApp a {data.get('jid', target)}: '{message}'"
            bridge_error = f"Error Baileys ({resp.status_code}): {resp.text}"
            if meta_error:
                return f"{meta_error} | Fallback Baileys falló: {bridge_error}"
            return bridge_error
    except Exception as e:
        bridge_error = f"Error al conectar con conector Baileys: {str(e)}"
        if meta_error:
            return f"{meta_error} | Fallback Baileys no disponible: {bridge_error}"
        return bridge_error
