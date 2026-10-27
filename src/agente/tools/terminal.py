import subprocess
from pathlib import Path
from agente.config import settings

def run_command(command: str, working_dir: str = "") -> str:
    """Ejecuta un comando en la consola (PowerShell en Windows) y devuelve la salida.
    
    Args:
        command: El comando a ejecutar (ej. 'git status', 'python test.py', 'npm test').
        working_dir: Carpeta donde ejecutarlo. Si se omite, usa la carpeta del proyecto.
    """
    cwd = working_dir if working_dir else settings.workspace_dir
    target_path = Path(cwd)
    if not target_path.exists():
        return f"Error: La ruta de trabajo '{cwd}' no existe."

    try:
        # Ejecutamos con PowerShell
        process = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
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
        return f"Error: El comando excedió el tiempo límite de 45 segundos."
    except Exception as e:
        return f"Error al ejecutar el comando: {str(e)}"
