import os
from pathlib import Path
from agente.config import settings

def _resolve_path(rel_or_abs_path: str) -> Path:
    p = Path(rel_or_abs_path)
    if not p.is_absolute():
        p = Path(settings.workspace_dir) / p
    return p.resolve()

def read_file(path: str, max_lines: int = 200) -> str:
    """Lee el contenido de un archivo de texto o código.
    
    Args:
        path: Ruta relativa o absoluta del archivo.
        max_lines: Máximo número de líneas a leer para no saturar el contexto.
    """
    try:
        target = _resolve_path(path)
        if not target.exists():
            return f"Error: El archivo '{path}' no existe en {target}."
        if target.is_dir():
            return f"Error: '{path}' es una carpeta, usa list_directory en su lugar."

        with open(target, "r", encoding="utf-8", errors="replace") as f:
            lines = [f.readline() for _ in range(max_lines)]
            content = "".join(lines)
            if f.readline():
                content += f"\n... (truncado a {max_lines} líneas)"
        return content
    except Exception as e:
        return f"Error al leer '{path}': {str(e)}"

def write_file(path: str, content: str, overwrite: bool = True) -> str:
    """Crea o sobreescribe un archivo en el proyecto.
    
    Args:
        path: Ruta relativa o absoluta donde guardar el archivo.
        content: Contenido de texto o código a escribir.
        overwrite: Si es True, reemplaza el contenido si el archivo ya existe.
    """
    try:
        target = _resolve_path(path)
        if target.exists() and not overwrite:
            return f"Error: El archivo '{path}' ya existe y overwrite=False."

        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Archivo '{target.name}' guardado exitosamente ({len(content)} caracteres)."
    except Exception as e:
        return f"Error al escribir en '{path}': {str(e)}"

def list_directory(path: str = ".", max_items: int = 50) -> str:
    """Lista los archivos y carpetas dentro de un directorio.
    
    Args:
        path: Carpeta a explorar (por defecto el proyecto actual).
        max_items: Cantidad máxima de elementos a devolver.
    """
    try:
        target = _resolve_path(path)
        if not target.exists():
            return f"Error: La carpeta '{path}' no existe."
        if not target.is_dir():
            return f"Error: '{path}' es un archivo, no una carpeta."

        entries = list(target.iterdir())
        output = [f"Directorio: {target}"]
        for i, entry in enumerate(entries[:max_items]):
            tipo = "[DIR]" if entry.is_dir() else "[FILE]"
            output.append(f"{tipo} {entry.name}")

        if len(entries) > max_items:
            output.append(f"... y {len(entries) - max_items} elementos más.")

        return "\n".join(output)
    except Exception as e:
        return f"Error al listar carpeta '{path}': {str(e)}"
