"""Canal de clientes por Kapso (WhatsApp Cloud API administrada por Kapso).

Flujo:
  Cliente escribe al número de Kapso -> Kapso envía `whatsapp.message.received`
  a POST /webhook/kapso -> se valida la firma -> se decide:
    * chat en modo humano (traspaso)  -> la IA no responde
    * el cliente pide a una persona / queja / reembolso -> se pausa la IA,
      se avisa a Sebastián y se le confirma al cliente que lo atenderá una persona
    * resto -> respuesta comercial de Sebax (sin herramientas) enviada por Kapso

Respuestas automáticas controladas por KAPSO_AUTO_REPLY:
  off  -> solo registra los mensajes, no responde
  test -> responde solo a KAPSO_TEST_NUMBERS y a los números del dueño (predeterminado)
  on   -> responde a todos los clientes
"""
import hashlib
import hmac
import json
import logging
import re
import time
import unicodedata
from collections import OrderedDict
from threading import Lock

import httpx

from agente.config import DATA_DIR, settings
from agente.security import number_in, phone_digits

logger = logging.getLogger(__name__)

HANDOFF_FILE = DATA_DIR / "kapso_handoff.json"
_handoff_lock = Lock()
_seen_ids: "OrderedDict[str, float]" = OrderedDict()
_SEEN_MAX = 2000

# Frases que activan el traspaso a una persona (se comparan sin acentos y en minúsculas).
HANDOFF_KEYWORDS = [
    # pide a una persona
    "humano", "una persona", "persona real", "asesor", "agente real", "hablar con alguien",
    "hablar con sebastian", "con el dueno", "atencion personal",
    "no eres real", "eres un bot", "eres bot", "quiero hablar con",
    # quejas, reembolsos, cobros y problemas con un servicio ya contratado
    "queja", "reclamo", "reembolso", "devolucion", "cancelar", "cancelacion",
    "factura", "ya pague", "me cobraron", "fraude",
    "molesto", "molesta", "enojado", "enojada", "pesimo", "no funciona",
    "abogado", "demanda", "profeco", "urgente",
]

CUSTOMER_HANDOFF_REPLY = (
    "Gracias por escribir a SSSSolutions. Le comunico con Sebastián Salinas para "
    "atenderle personalmente; le responderá por este mismo chat en cuanto esté disponible."
)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text.lower()).strip()


def needs_human(text: str) -> str | None:
    """Devuelve la frase que activó el traspaso, o None si la IA puede responder."""
    norm = _normalize(text)
    for kw in HANDOFF_KEYWORDS:
        if re.search(r"(?<![a-z])" + re.escape(kw) + r"(?![a-z])", norm):
            return kw
    return None


# ---------------------------------------------------------------- firma / idempotencia

def verify_signature(raw_body: bytes, signature: str | None) -> bool:
    """HMAC-SHA256 hex del cuerpo crudo con KAPSO_WEBHOOK_SECRET (header X-Webhook-Signature)."""
    secret = settings.kapso_webhook_secret
    if not secret:
        logger.error("Webhook de Kapso rechazado: KAPSO_WEBHOOK_SECRET no está configurado.")
        return False
    if not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip())


def already_processed(key: str | None) -> bool:
    """True si este mensaje ya se procesó (Kapso puede reenviar el mismo evento)."""
    if not key:
        return False
    if key in _seen_ids:
        return True
    _seen_ids[key] = time.time()
    while len(_seen_ids) > _SEEN_MAX:
        _seen_ids.popitem(last=False)
    return False


# ---------------------------------------------------------------- traspaso a humano

def _load_handoffs() -> dict:
    try:
        return json.loads(HANDOFF_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_handoffs(data: dict) -> None:
    HANDOFF_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _key(number: str) -> str:
    digits = phone_digits(number)
    return digits[-10:] if len(digits) >= 10 else digits


def is_paused(number: str) -> bool:
    """True si el chat está en manos de una persona. Expira tras KAPSO_HANDOFF_HOURS."""
    key = _key(number)
    with _handoff_lock:
        data = _load_handoffs()
        entry = data.get(key)
        if not entry:
            return False
        hours = settings.kapso_handoff_hours
        if hours > 0 and time.time() - entry.get("since", 0) > hours * 3600:
            data.pop(key, None)
            _save_handoffs(data)
            logger.info("Traspaso de %s expirado; la IA vuelve a responder.", key)
            return False
        return True


def pause(number: str, reason: str) -> None:
    key = _key(number)
    with _handoff_lock:
        data = _load_handoffs()
        data[key] = {"since": time.time(), "reason": reason, "number": phone_digits(number)}
        _save_handoffs(data)


def resume(number: str) -> bool:
    key = _key(number)
    with _handoff_lock:
        data = _load_handoffs()
        existed = data.pop(key, None) is not None
        _save_handoffs(data)
    return existed


def list_paused() -> dict:
    with _handoff_lock:
        return _load_handoffs()


def handle_owner_command(text: str) -> str | None:
    """Comandos del dueño para el traspaso. Devuelve la respuesta o None si no es un comando.

    /humano <numero>  -> la IA deja de responder a ese cliente
    /bot <numero>     -> la IA vuelve a responder a ese cliente
    /pausados         -> lista los chats en modo humano
    """
    parts = (text or "").strip().split()
    if not parts:
        return None
    cmd = parts[0].lower()
    arg = "".join(parts[1:])
    if cmd in ("/pausados", "/humanos"):
        paused = list_paused()
        if not paused:
            return "No hay chats de clientes en modo humano."
        lines = [f"+{v.get('number', k)} (motivo: {v.get('reason', '-')})" for k, v in paused.items()]
        return "Chats en modo humano:\n" + "\n".join(lines)
    if cmd in ("/humano", "/bot"):
        if not phone_digits(arg):
            return f"Uso: {cmd} <numero del cliente>"
        if cmd == "/humano":
            pause(arg, "manual")
            return f"Listo. Sebax deja de responder a +{phone_digits(arg)} hasta que envíes /bot {phone_digits(arg)}."
        resume(arg)
        return f"Listo. Sebax vuelve a responder a +{phone_digits(arg)}."
    return None


# ---------------------------------------------------------------- envío

def send_text(to_number: str, body: str) -> tuple[bool, str]:
    """Envía un texto por la API de WhatsApp de Kapso. Devuelve (ok, detalle)."""
    if not (settings.kapso_api_key and settings.kapso_phone_number_id):
        return False, "Kapso no configurado (KAPSO_API_KEY / KAPSO_PHONE_NUMBER_ID)."
    to = phone_digits(to_number)
    if not to:
        return False, "Número de destino no válido."
    url = f"{settings.kapso_api_base.rstrip('/')}/{settings.kapso_phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": True, "body": body[:4096]},
    }
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(
                url,
                headers={"X-API-Key": settings.kapso_api_key, "Content-Type": "application/json"},
                json=payload,
            )
        if resp.status_code in (200, 201):
            msg_id = next((m.get("id") for m in resp.json().get("messages", []) if m.get("id")), "")
            return True, f"Entrega confirmada por Kapso a +{to} (id: {msg_id or 'confirmado'})."
        return False, f"Error Kapso ({resp.status_code}): {resp.text[:500]}"
    except Exception as e:  # noqa: BLE001
        return False, f"Error al comunicar con Kapso: {e}"


# ---------------------------------------------------------------- eventos entrantes

def extract_messages(event: dict) -> list[dict]:
    """Normaliza el cuerpo (simple o en lote) a [{id, sender, text, name}] de mensajes entrantes."""
    items = event.get("data") if event.get("batch") else [event]
    out = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        msg = item.get("message") or {}
        conv = item.get("conversation") or {}
        kapso_meta = msg.get("kapso") or {}
        if kapso_meta.get("direction", "inbound") != "inbound" or kapso_meta.get("passive"):
            continue
        sender = msg.get("from") or conv.get("phone_number") or ""
        text = ((msg.get("text") or {}).get("body") or kapso_meta.get("content") or "").strip()
        if sender and text:
            out.append({
                "id": msg.get("id"),
                "sender": phone_digits(sender),
                "text": text,
                "name": conv.get("contact_name") or "",
            })
    return out


def auto_reply_allowed(sender: str, is_owner: bool) -> bool:
    mode = settings.kapso_auto_reply
    if mode == "on":
        return True
    if mode == "test":
        return is_owner or number_in(sender, settings.kapso_test_numbers)
    return False
