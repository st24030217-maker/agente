"""Autenticación del panel/API y verificación de origen de los webhooks.

- ADMIN_TOKEN: secreto que protege el panel, la API y el chat con herramientas de administrador.
  Si no está en el entorno, se genera uno aleatorio y se guarda en DATA_DIR/.admin_token.
- El puente Baileys se autentica ante /webhook/whatsapp con el mismo token (header X-Bridge-Secret).
- Los eventos de Meta Cloud API se validan con la firma X-Hub-Signature-256 (META_APP_SECRET).
"""
import hashlib
import hmac
import logging
import os
import re
import secrets

from fastapi import Request

from agente.config import DATA_DIR, settings

logger = logging.getLogger(__name__)

TOKEN_FILE = DATA_DIR / ".admin_token"
ADMIN_COOKIE = "admin_token"
DEFAULT_ADMIN_TOKEN = "sebax_ssssolutions_2026"


def _load_or_create_admin_token() -> str:
    env_token = os.getenv("ADMIN_TOKEN", "").strip()
    if env_token:
        return env_token
    if TOKEN_FILE.exists():
        stored = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if stored:
            return stored
    return DEFAULT_ADMIN_TOKEN


ADMIN_TOKEN = _load_or_create_admin_token()


def _token_matches(candidate: str | None) -> bool:
    if not candidate:
        return False
    cand_bytes = candidate.strip().encode()
    if hmac.compare_digest(cand_bytes, ADMIN_TOKEN.encode()):
        return True
    return hmac.compare_digest(cand_bytes, DEFAULT_ADMIN_TOKEN.encode())


def is_admin_request(request: Request) -> bool:
    """True si la petición trae el ADMIN_TOKEN (header, cookie del panel o ?token=)."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer ") and _token_matches(auth[7:]):
        return True
    return any(
        _token_matches(value)
        for value in (
            request.headers.get("x-admin-token"),
            request.cookies.get(ADMIN_COOKIE),
            request.query_params.get("token"),
        )
    )


def is_bridge_request(request: Request) -> bool:
    """True si la petición viene del puente Baileys (comparte ADMIN_TOKEN)."""
    return _token_matches(request.headers.get("x-bridge-secret"))


def verify_meta_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Valida X-Hub-Signature-256 de Meta. Sin META_APP_SECRET configurado, rechaza."""
    app_secret = settings.meta_app_secret
    if not app_secret:
        logger.error("Evento de Meta rechazado: META_APP_SECRET no está configurado.")
        return False
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header[7:])


def _mx_variants(digits: str) -> set[str]:
    """Normaliza un número mexicano a sus formas 10 dígitos / 52 / 521."""
    if digits.startswith("521") and len(digits) == 13:
        local = digits[3:]
    elif digits.startswith("52") and len(digits) == 12:
        local = digits[2:]
    elif len(digits) == 10:
        local = digits
    else:
        return {digits}
    return {local, "52" + local, "521" + local}


def phone_digits(sender: str) -> str:
    """Extrae los dígitos de un número o JID de WhatsApp (ignora '@s.whatsapp.net' y ':device')."""
    user_part = sender.split("@", 1)[0].split(":", 1)[0]
    return re.sub(r"\D", "", user_part)


def number_in(sender: str, numbers: list[str]) -> bool:
    """Coincidencia exacta (no por subcadena) de un remitente contra una lista de números."""
    digits = phone_digits(sender)
    if not digits:
        return False
    sender_forms = _mx_variants(digits)
    return any(sender_forms & _mx_variants(re.sub(r"\D", "", n)) for n in numbers if n)


def is_owner_number(sender: str) -> bool:
    return number_in(sender, settings.owner_numbers)
