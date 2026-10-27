import sys
import os
import time
import subprocess
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SUPERVISOR 24/7]: %(message)s"
)
logger = logging.getLogger("supervisor")

BASE_DIR = Path(__file__).resolve().parent

# Evitar que Windows entre en modo suspensión mientras Sebax está activo
def prevent_windows_sleep():
    try:
        import ctypes
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_AWAYMODE_REQUIRED = 0x00000040
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
        )
        logger.info("Modo Always-On 24/7 activado en Windows (Prevención de suspensión del sistema).")
    except Exception as e:
        logger.warning("No se pudo configurar estado de energía: %s", e)

def get_python_exe() -> str:
    venv_py = BASE_DIR / ".venv" / "Scripts" / "python.exe"
    if venv_py.exists():
        return str(venv_py)
    return sys.executable

def get_cloudflared_exe() -> str:
    user_home = Path(os.environ.get("USERPROFILE", ""))
    bin_cf = user_home / ".local" / "bin" / "cloudflared.exe"
    if bin_cf.exists():
        return str(bin_cf)
    return "cloudflared"

class ProcessGuardian:
    def __init__(self, name: str, cmd: list, cwd: Path):
        self.name = name
        self.cmd = cmd
        self.cwd = cwd
        self.process = None

    def start(self):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONPATH"] = str(BASE_DIR / "src")
        env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
        
        logger.info("Iniciando servicio [%s]...", self.name)
        try:
            self.process = subprocess.Popen(
                self.cmd,
                cwd=str(self.cwd),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            logger.info("Servicio [%s] iniciado con PID %d.", self.name, self.process.pid)
        except Exception as e:
            logger.error("Error al iniciar servicio [%s]: %s", self.name, e)

    def is_alive(self) -> bool:
        if self.process is None:
            return False
        return self.process.poll() is None

    def check_and_recover(self):
        if not self.is_alive():
            logger.warning("ALERTA: El servicio [%s] se detuvo. Reiniciando de inmediato...", self.name)
            self.start()

    def stop(self):
        if self.process and self.is_alive():
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass

def main():
    logger.info("Iniciando guardián 24/7 de Sebax (SSSSolutions)...")
    prevent_windows_sleep()

    py_exe = get_python_exe()
    cf_exe = get_cloudflared_exe()

    services = [
        ProcessGuardian(
            name="FastAPI-Core",
            cmd=[py_exe, "-m", "uvicorn", "agente.main:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=BASE_DIR
        ),
        ProcessGuardian(
            name="WhatsApp-Bridge",
            cmd=["node", "index.js"],
            cwd=BASE_DIR / "bridge"
        ),
        ProcessGuardian(
            name="Cloudflare-Tunnel",
            cmd=[cf_exe, "tunnel", "--url", "http://127.0.0.1:8000"],
            cwd=BASE_DIR
        )
    ]

    for s in services:
        s.start()
        time.sleep(2)

    logger.info("Todos los servicios iniciados. Monitoreando 24/7...")

    try:
        while True:
            time.sleep(4)
            for s in services:
                s.check_and_recover()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Deteniendo supervisor 24/7 y servicios...")
        for s in services:
            s.stop()

if __name__ == "__main__":
    main()
