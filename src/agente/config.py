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
        for num in os.getenv("ALLOWED_NUMBERS", "").split(",") 
        if num.strip()
    ]
    # Directorio de trabajo predeterminado para herramientas de código y terminal
    workspace_dir: str = os.getenv("WORKSPACE_DIR", str(BASE_DIR))
    server_port: int = int(os.getenv("PORT", "8000"))
    server_host: str = os.getenv("HOST", "0.0.0.0")
    bridge_port: int = int(os.getenv("BRIDGE_PORT", "3000"))

settings = Settings()
