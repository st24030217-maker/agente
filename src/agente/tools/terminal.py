import subprocess
import re
from pathlib import Path
from agente.config import settings

# Comandos y patrones de riesgo bloqueados por política de seguridad
DANGEROUS_PATTERNS = [
    r"\bformat\b",
    r"\bdel\s+/[sfq]",
    r"\brmdir\s+/[sq]",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bstop-computer\b",
    r"\brestart-computer\b",
    r"\bset-executionpolicy\b",
    r"-encodedcommand",
    r"-enc\b",
    r"\bmkfs\b",
    r":\(\)\s*\{\s*:\|\:&\s*\};:", # fork bomb
]

def run_command(command: str, working_dir: str = "") -> str:
    """Ejecuta un comando en la consola de manera segura dentro del entorno de trabajo.
    
    Args:
        command: El comando a ejecutar (ej. 'git status', 'python test.py', 'npm test').
        working_dir: Carpeta donde ejecutarlo. Si se omite, usa la carpeta del proyecto.
    """
    clean_cmd = command.strip()
    if not clean_cmd:
        return "Error: Comando vacío."

    # Validación defensiva contra comandos destructivos o evasivos
    cmd_lower = clean_cmd.lower()
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd_lower):
            return f"Bloqueado por política de seguridad: el comando contiene patrones no permitidos ('{pattern}')."

    cwd = working_dir if working_dir else settings.workspace_dir
    target_path = Path(cwd).resolve()
    
    # Confinar la ejecución al directorio de trabajo permitido
    workspace_root = Path(settings.workspace_dir).resolve()
    if not (target_path == workspace_root or target_path.is_relative_to(workspace_root)):
        return f"Bloqueado por seguridad: la ruta de trabajo '{cwd}' está fuera del proyecto permitido."

    if not target_path.exists():
        return f"Error: La ruta de trabajo '{cwd}' no existe."

    try:
        process = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", clean_cmd],
            cwd=str(target_path),
            capture_output=True,
            text=True,
            timeout=45,
            encoding="utf-8",
            errors="replace"
        )
        stdout = process.stdout.strip()
        stderr = process.stderr.strip()
        code = process.returncode

        output_parts = []
        if stdout:
            output_parts.append(f"STDOUT:\n{stdout}")
        if stderr:
            output_parts.append(f"STDERR:\n{stderr}")
        if not output_parts:
            output_parts.append("(Comando ejecutado con éxito sin salida de texto)")

        return f"[Exit code {code}]\n" + "\n\n".join(output_parts)
    except subprocess.TimeoutExpired:
        return "Error: El comando excedió el tiempo límite de 45 segundos."
    except Exception as e:
        return f"Error al ejecutar el comando: {str(e)}"
