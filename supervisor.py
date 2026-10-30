import sys
import os
import time
import shutil
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
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)


def prevent_windows_sleep():
    """Evita que Windows entre en modo suspensión mientras Sebax está activo."""
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


def get_cloudflared_exe() -> str | None:
    candidates = [
        Path(os.environ.get("USERPROFILE", "")) / ".local" / "bin" / "cloudflared.exe",
        Path("C:/Program Files/cloudflared/cloudflared.exe"),
        Path("C:/Program Files (x86)/cloudflared/cloudflared.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    path_hit = shutil.which("cloudflared")
    if path_hit:
        return path_hit

    return None


class ProcessGuardian:
    def __init__(self, name: str, cmd: list, cwd: Path):
        self.name = name
        self.cmd = cmd
        self.cwd = cwd
        self.process = None
        self.log_path = LOG_DIR / f"{name.lower().replace(' ', '_')}.log"
        self.stdout_handle = None
        self.stderr_handle = None
        self._restart_delay = 1.0
        self._next_retry_at = 0.0

    def _open_log_files(self):
        self.stdout_handle = open(self.log_path, "ab", buffering=0)
        self.stderr_handle = open(self.log_path, "ab", buffering=0)

    def _close_log_files(self):
        for handle in (self.stdout_handle, self.stderr_handle):
            if handle is not None:
                try:
                    handle.close()
                except Exception:
                    pass
        self.stdout_handle = None
        self.stderr_handle = None

    def start(self):
        if self.process is not None and self.is_alive():
            return

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONPATH"] = str(BASE_DIR / "src")

        logger.info("Iniciando servicio [%s]...", self.name)
        self._open_log_files()
        try:
            self.process = subprocess.Popen(
                self.cmd,
                cwd=str(self.cwd),
                env=env,
                stdout=self.stdout_handle,
                stderr=self.stderr_handle,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            logger.info("Servicio [%s] iniciado con PID %d.", self.name, self.process.pid)
            self._restart_delay = 1.0
            self._next_retry_at = 0.0
        except Exception as e:
            self._close_log_files()
            logger.error("Error al iniciar servicio [%s]: %s", self.name, e)

    def is_alive(self) -> bool:
        if self.process is None:
            return False
        return self.process.poll() is None

    def _kill_tree(self):
        if self.process is None:
            return

        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=10,
                )
            else:
                self.process.terminate()
                self.process.wait(timeout=3)
        except Exception:
            try:
                self.process.kill()
            except Exception:
                pass

    def check_and_recover(self):
        if self.is_alive():
            return

        now = time.monotonic()
        if now < self._next_retry_at:
            return

        logger.warning("ALERTA: El servicio [%s] se detuvo. Reiniciando con backoff %ss...", self.name, self._restart_delay)
        self.start()
        if self.is_alive():
            self._restart_delay = 1.0
        else:
            self._restart_delay = min(self._restart_delay * 2, 30.0)
            self._next_retry_at = now + self._restart_delay

    def stop(self):
        if self.process is not None:
            self._kill_tree()
        self._close_log_files()


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
    ]

    if cf_exe:
        services.append(
            ProcessGuardian(
                name="Cloudflare-Tunnel",
                cmd=[cf_exe, "tunnel", "--url", "http://127.0.0.1:8000"],
                cwd=BASE_DIR
            )
        )
    else:
        logger.warning("cloudflared no está instalado o no se encontró en PATH. Se omite el túnel Cloudflare.")

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
