import json
from datetime import datetime
from pathlib import Path
from agente.config import DATA_DIR

NOTES_FILE = DATA_DIR / "notes.json"

def _load_notes() -> dict:
    if not NOTES_FILE.exists():
        return {}
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_notes(notes: dict):
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)

def add_note_or_task(title: str, content: str, tag: str = "general") -> str:
    """Guarda una nota, tarea o recordatorio diario para consultarlo más adelante.
    
    Args:
        title: Título identificador o resumen de la tarea.
        content: Detalles, pasos, código o descripción.
        tag: Categoría (ej. 'tarea', 'idea', 'bug', 'recordatorio').
    """
    notes = _load_notes()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    notes[title] = {
        "title": title,
        "content": content,
        "tag": tag,
        "created_at": now,
        "updated_at": now
    }
    _save_notes(notes)
    return f"Nota/Tarea '{title}' guardada exitosamente bajo categoría '[{tag}]'."

def list_notes_and_tasks(tag: str = "") -> str:
    """Lista las notas, pendientes y tareas guardadas.
    
    Args:
        tag: Opcional, filtrar por categoría (ej. 'tarea'). Si está vacío lista todo.
    """
    notes = _load_notes()
    if not notes:
        return "No tienes notas ni tareas pendientes guardadas actualmente."

    filtered = notes.values()
    if tag:
        filtered = [n for n in filtered if n.get("tag", "").lower() == tag.lower()]

    if not filtered:
        return f"No se encontraron notas con la categoría '{tag}'."

    res = ["NOTAS Y TAREAS GUARDADAS:"]
    for n in filtered:
        res.append(f"• [{n.get('tag', 'general').upper()}] {n['title']} (Creado: {n.get('created_at', '')}):\n  {n['content']}")
    return "\n\n".join(res)

def delete_note_or_task(title: str) -> str:
    """Elimina una nota o tarea completada.
    
    Args:
        title: Título exacto de la nota a eliminar.
    """
    notes = _load_notes()
    if title in notes:
        del notes[title]
        _save_notes(notes)
        return f"Nota o tarea '{title}' eliminada exitosamente."
    return f"No se encontró ninguna nota con el título '{title}'."
