import httpx
from agente.config import settings

def send_whatsapp_message(to_number: str, message: str) -> str:
    """Envía un mensaje de texto por WhatsApp a un número o a ti mismo.
    
    Args:
        to_number: Número de teléfono con código de país (ej. '5218719164677'). Si se deja vacío o 'self', se envía a ti mismo.
        message: El texto que deseas enviar.
    """
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
