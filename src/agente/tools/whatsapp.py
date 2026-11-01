import logging
import httpx
from agente.config import settings

logger = logging.getLogger(__name__)

def send_whatsapp_message(to_number: str, message: str) -> str:
    """Envía un mensaje de texto por WhatsApp a un número o a ti mismo.
    Si WHATSAPP_PROVIDER es 'cloud_api', usa prioritariamente Meta WhatsApp Business Cloud API Oficial.
    Si es 'baileys', usa prioritariamente el conector local Baileys.
    """
    meta_error = None
    bridge_error = None

    def _send_meta(target_num: str) -> str | None:
        if not (settings.meta_wa_token and settings.meta_wa_phone_number_id):
            return "Credenciales de Meta Cloud API no configuradas."
        clean_target = "".join(filter(str.isdigit, target_num))
        if clean_target.startswith("521") and len(clean_target) == 13:
            clean_target = "52" + clean_target[3:]
        elif len(clean_target) == 10:
            clean_target = "52" + clean_target
        if not clean_target:
            return "Número de teléfono no válido."
        
        headers = {
            "Authorization": f"Bearer {settings.meta_wa_token}",
            "Content-Type": "application/json"
        }
        url = f"https://graph.facebook.com/v20.0/{settings.meta_wa_phone_number_id}/messages"
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
                    data = resp.json()
                    message_id = next(
                        (item.get("id") for item in data.get("messages", []) if item.get("id")),
                        None
                    )
                    return f"Entrega confirmada por Meta WhatsApp Cloud API a +{clean_target} (id: {message_id or 'confirmado'})."
                return f"Error Meta API ({resp.status_code}): {resp.text}"
        except Exception as e:
            return f"Error al comunicar con Meta WhatsApp Cloud API: {str(e)}"

    def _send_baileys(target_num: str) -> str | None:
        try:
            bridge_status_url = f"http://127.0.0.1:{settings.bridge_port}/status"
            with httpx.Client(timeout=3.0) as client:
                st = client.get(bridge_status_url)
                if st.status_code == 200 and st.json().get("status") == "open":
                    bridge_url = f"http://127.0.0.1:{settings.bridge_port}/send"
                    target = "" if target_num.lower() in ["self", "yo", "mismo", ""] else target_num
                    payload = {"to": target, "text": message}
                    resp = client.post(bridge_url, json=payload, timeout=20.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("delivered") is True or data.get("accepted") is True:
                            return f"Entrega confirmada por WhatsApp a {data.get('jid', target)} (estado: {data.get('delivery_status', 'confirmado')})."
                        return "El conector Baileys no confirmó la entrega."
                    return f"Error Baileys ({resp.status_code}): {resp.text}"
                return "Conector Baileys no conectado (status != open)."
        except Exception as e:
            return f"Conector Baileys no disponible: {str(e)}"

    target = to_number.strip()
    if target.lower() in ["self", "yo", "mismo", ""]:
        target = settings.allowed_numbers[0] if settings.allowed_numbers else "8719164677"

    # Orden de proveedores según configuración activa
    if settings.whatsapp_provider == "cloud_api":
        res = _send_meta(target)
        if res and res.startswith("Entrega confirmada"):
            return res
        meta_error = res
        # Fallback a Baileys si Meta falla
        res_b = _send_baileys(target)
        if res_b and res_b.startswith("Entrega confirmada"):
            return res_b
        bridge_error = res_b
    else:
        res = _send_baileys(target)
        if res and res.startswith("Entrega confirmada"):
            return res
        bridge_error = res
        # Fallback a Meta
        res_m = _send_meta(target)
        if res_m and res_m.startswith("Entrega confirmada"):
            return res_m
        meta_error = res_m

    if bridge_error and meta_error:
        return f"Fallo al enviar mensaje: {meta_error} | {bridge_error}"
    return meta_error or bridge_error or "No se pudo enviar el mensaje (canales no disponibles)."


def is_delivery_confirmed(result: str) -> bool:
    return result.startswith("Entrega confirmada por WhatsApp")


def is_delivery_pending(result: str) -> bool:
    return result.startswith(("Aceptado por el puente", "Aceptado por Meta"))
