import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data"))).expanduser()
if not DATA_DIR.is_absolute():
    DATA_DIR = BASE_DIR / DATA_DIR
DATA_DIR.mkdir(parents=True, exist_ok=True)
WHATSAPP_AUTH_DIR = Path(os.getenv(
    "WHATSAPP_AUTH_DIR",
    str(BASE_DIR / "bridge" / "auth_info_baileys")
)).expanduser()
if not WHATSAPP_AUTH_DIR.is_absolute():
    WHATSAPP_AUTH_DIR = BASE_DIR / WHATSAPP_AUTH_DIR

def _csv_env(name: str, default: str = "") -> list[str]:
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]

_DEFAULT_OWNERS = "8719164677,8718321968"

class Settings(BaseModel):
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    # Números del dueño: reciben herramientas de administrador por WhatsApp.
    owner_numbers: list[str] = _csv_env("OWNER_NUMBERS", _DEFAULT_OWNERS)
    # Lista blanca de números a los que Sebax responde por WhatsApp con el agente.
    # Si ALLOWED_NUMBERS está vacío, solo responde a los números del dueño.
    allowed_numbers: list[str] = _csv_env("ALLOWED_NUMBERS") or _csv_env("OWNER_NUMBERS", _DEFAULT_OWNERS)
    # Directorio de trabajo predeterminado para herramientas de código y terminal
    workspace_dir: str = os.getenv("WORKSPACE_DIR") or str(BASE_DIR)
    server_port: int = int(os.getenv("PORT", "8000"))
    server_host: str = os.getenv("HOST", "0.0.0.0")
    bridge_port: int = int(os.getenv("BRIDGE_PORT", "3000"))
    # "cloud_api" = Meta WhatsApp Cloud API como canal principal; "baileys" = WhatsApp Web (QR).
    # Cada uno usa al otro como respaldo para enviar si falla.
    whatsapp_provider: str = os.getenv("WHATSAPP_PROVIDER", "baileys").strip().lower()
    whatsapp_auth_dir: str = str(WHATSAPP_AUTH_DIR)
    # Meta WhatsApp Cloud API: SOLO desde .env, nunca valores reales en el código
    meta_wa_token: str = os.getenv("META_WA_TOKEN", "")
    meta_wa_phone_number_id: str = os.getenv("META_WA_PHONE_NUMBER_ID", "")
    meta_wa_verify_token: str = os.getenv("META_WA_VERIFY_TOKEN", "")
    # App Secret de Meta para validar la firma X-Hub-Signature-256 del webhook
    meta_app_secret: str = os.getenv("META_APP_SECRET", "")
    # Kapso (canal de clientes). La API key SOLO desde el entorno, nunca en el código.
    kapso_api_key: str = os.getenv("KAPSO_API_KEY", "")
    kapso_phone_number_id: str = os.getenv("KAPSO_PHONE_NUMBER_ID", "")
    kapso_webhook_secret: str = os.getenv("KAPSO_WEBHOOK_SECRET", "")
    kapso_api_base: str = os.getenv("KAPSO_API_BASE", "https://api.kapso.ai/meta/whatsapp/v24.0")
    # off = no responde | test = solo KAPSO_TEST_NUMBERS y el dueño | on = todos los clientes
    kapso_auto_reply: str = os.getenv("KAPSO_AUTO_REPLY", "test").strip().lower()
    kapso_test_numbers: list[str] = _csv_env("KAPSO_TEST_NUMBERS")
    # Horas que la IA permanece en silencio tras un traspaso a humano (0 = hasta /bot <numero>)
    kapso_handoff_hours: float = float(os.getenv("KAPSO_HANDOFF_HOURS", "24"))
    # Google Maps / Places API vía Serper
    serper_api_key: str = os.getenv("SERPER_API_KEY", "")

settings = Settings()
