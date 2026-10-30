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

class Settings(BaseModel):
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    # Lista blanca de números autorizados separados por coma con código de país.
    # Si se deja vacío (por defecto), Sebax responderá como agente comercial público a cualquier chat que le escriba.
    allowed_numbers: list[str] = [
        num.strip() 
        for num in os.getenv("ALLOWED_NUMBERS", "").split(",") 
        if num.strip()
    ]
    # Directorio de trabajo predeterminado para herramientas de código y terminal
    workspace_dir: str = os.getenv("WORKSPACE_DIR") or str(BASE_DIR)
    server_port: int = int(os.getenv("PORT", "8000"))
    server_host: str = os.getenv("HOST", "0.0.0.0")
    bridge_port: int = int(os.getenv("BRIDGE_PORT", "3000"))
    whatsapp_auth_dir: str = str(WHATSAPP_AUTH_DIR)
    # Meta WhatsApp Cloud API credentials must be provided through the environment.
    meta_wa_token: str = os.getenv("META_WA_TOKEN", "")
    meta_wa_phone_number_id: str = os.getenv("META_WA_PHONE_NUMBER_ID", "")
    meta_wa_verify_token: str = os.getenv("META_WA_VERIFY_TOKEN", "")

settings = Settings()
