import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

class Settings(BaseModel):
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    allowed_numbers: list[str] = [
        num.strip() 
        for num in os.getenv("ALLOWED_NUMBERS", "528719164677,5218719164677").split(",") 
        if num.strip()
    ]
    # Directorio de trabajo predeterminado para herramientas de código y terminal
    workspace_dir: str = os.getenv("WORKSPACE_DIR") or str(BASE_DIR)
    server_port: int = int(os.getenv("PORT", "8000"))
    server_host: str = os.getenv("HOST", "0.0.0.0")
    bridge_port: int = int(os.getenv("BRIDGE_PORT", "3000"))
    # Meta WhatsApp Cloud API Oficial (Token Permanente de Usuario del Sistema)
    meta_wa_token: str = os.getenv("META_WA_TOKEN", "EAAUyJT420vsBSyU0ZAn4jnpz2NncsPYCT1b2EsjCFaqZBIUykb11qWGY9G5YZCYTkRb9pfEwsapllwgyIY9scM2NBfOsWMEUL9YpPzZBcqbwh5TIJiYn5woGVx88WvrJYrx2hGt8NInFdkyZA5a6DOhkeePuQrSB6itn8ptc6qDvIYJwE7ZCjEtW1bMbylLgZDZD")
    meta_wa_phone_number_id: str = os.getenv("META_WA_PHONE_NUMBER_ID", "1362013893668994")
    meta_wa_verify_token: str = os.getenv("META_WA_VERIFY_TOKEN", "sebax_ssssolutions_2026")

settings = Settings()
