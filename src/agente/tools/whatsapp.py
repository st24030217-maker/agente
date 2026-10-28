import httpx
from agente.config import settings

def send_whatsapp_message(to_number: str, message: str) -> str:
    """Envía un mensaje de texto por WhatsApp a un número o a ti mismo.
    Soporta tanto Meta WhatsApp Cloud API Oficial como el puente Baileys.
    
    Args:
        to_number: Número de teléfono con código de país (ej. '5218719164677'). Si se deja vacío o 'self', se envía a ti mismo.
        message: El texto que deseas enviar.
    """
    # 1. Modo Meta WhatsApp Business Cloud API Oficial
    if settings.meta_wa_token and settings.meta_wa_phone_number_id:
        target = to_number.strip()
        if target.lower() in ["self", "yo", "mismo", ""]:
            target = settings.allowed_numbers[0] if settings.allowed_numbers else ""
        
        clean_target = "".join(filter(str.isdigit, target))
        if not clean_target:
            return "Error: Número de destinatario no válido para WhatsApp Cloud API."

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
                return f"Error Meta API ({resp.status_code}): {resp.text}"
        except Exception as e:
            return f"Error al comunicar con Meta WhatsApp Cloud API: {str(e)}"

    # 2. Modo Puente Baileys Local
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
            return f"Error al enviar mensaje por WhatsApp (Status {resp.status_code}): {resp.text}"
    except Exception as e:
        return f"Error al conectar con el conector de WhatsApp: {str(e)}"
