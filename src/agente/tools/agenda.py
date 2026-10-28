import json
import logging
from datetime import datetime
from pathlib import Path

from agente.config import DATA_DIR
from agente.tools.whatsapp import send_whatsapp_message

logger = logging.getLogger(__name__)

APPOINTMENTS_FILE = DATA_DIR / "appointments.json"

def _load_appointments() -> list:
    if not APPOINTMENTS_FILE.exists():
        return []
    try:
        with open(APPOINTMENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _save_appointments(appointments: list):
    with open(APPOINTMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(appointments, f, indent=2, ensure_ascii=False)

def add_appointment(business_name: str, client_name: str = "", phone: str = "", date_time: str = "", notes: str = "", status: str = "confirmada") -> str:
    """Agenda una cita o reunión de negocios con un cliente potencial de SSSSolutions y notifica de inmediato a Sebastián por WhatsApp.
    
    Args:
        business_name: Nombre de la empresa o negocio del cliente.
        client_name: Nombre de la persona de contacto.
        phone: Teléfono o WhatsApp de contacto.
        date_time: Fecha y hora acordada (ej. 'Mañana a las 11:00 AM' o '2026-10-30 16:00').
        notes: Observaciones o temas a tratar en la reunión (ej. 'Interesado en cotización de sitio web con menú digital').
        status: Estado inicial ('confirmada', 'pendiente', 'en_negociacion').
    """
    appointments = _load_appointments()
    app_id = len(appointments) + 1
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    appointment = {
        "id": app_id,
        "business_name": business_name,
        "client_name": client_name or business_name,
        "phone": phone,
        "date_time": date_time,
        "notes": notes,
        "status": status,
        "created_at": now
    }
    appointments.append(appointment)
    _save_appointments(appointments)

    # Notificar inmediatamente a Sebastián Salinas en su WhatsApp personal
    alert_msg = (
        f"NUEVA CITA AGENDADA - SSSSOLUTIONS\n\n"
        f"Cliente: {business_name} ({client_name or 'Contacto directo'})\n"
        f"Teléfono: {phone}\n"
        f"Fecha y Hora: {date_time}\n"
        f"Notas: {notes or 'Sin observaciones adicionales'}\n"
        f"Estado: {status.upper()}\n\n"
        f"Registrada por Sebax en la agenda del agente."
    )
    try:
        send_whatsapp_message(to_number="self", message=alert_msg)
    except Exception as e:
        logger.warning("Fallo al enviar notificación de cita a Sebastián: %s", e)

    return f"Cita ID {app_id} agendada con éxito para [{business_name}] el [{date_time}]. Notificación enviada al WhatsApp de Sebastián."

def list_appointments(status_filter: str = "") -> str:
    """Lista las citas y llamadas agendadas en la agenda de SSSSolutions.
    
    Args:
        status_filter: Opcional, filtrar por estado ('confirmada', 'pendiente', 'completada', 'cancelada').
    """
    appointments = _load_appointments()
    if not appointments:
        return "No hay citas registradas en la agenda actualmente."

    filtered = appointments
    if status_filter:
        filtered = [a for a in appointments if a.get("status", "").lower() == status_filter.lower()]

    if not filtered:
        return f"No se encontraron citas con estado '{status_filter}'."

    lines = [f"CITAS AGENDADAS ({len(filtered)}):"]
    for a in sorted(filtered, key=lambda x: x.get("id", 0), reverse=True):
        lines.append(
            f"• ID {a['id']}: [{a.get('status', 'confirmada').upper()}] {a['business_name']} ({a.get('client_name', '')}) "
            f"| Fecha: {a.get('date_time', 'Por acordar')} | Tel: {a.get('phone', '')}"
        )
        if a.get("notes"):
            lines.append(f"  Notas: {a['notes']}")
    return "\n".join(lines)

def update_appointment_status(appointment_id: int, status: str, notes: str = "") -> str:
    """Actualiza el estado de una cita (ej. 'confirmada', 'completada', 'cancelada', 'reprogramada')."""
    appointments = _load_appointments()
    for a in appointments:
        if a.get("id") == appointment_id:
            a["status"] = status.lower()
            if notes:
                a["notes"] = (a.get("notes", "") + f" | {notes}").strip(" | ")
            _save_appointments(appointments)
            return f"Cita ID {appointment_id} [{a['business_name']}] actualizada a '{status}'."
    return f"No se encontró ninguna cita con ID {appointment_id}."

def get_appointments_stats() -> dict:
    """Devuelve estadísticas y lista de citas para la interfaz web y API."""
    appointments = _load_appointments()
    total = len(appointments)
    confirmadas = sum(1 for a in appointments if a.get("status") == "confirmada")
    pendientes = sum(1 for a in appointments if a.get("status") in ["pendiente", "en_negociacion"])
    completadas = sum(1 for a in appointments if a.get("status") == "completada")

    return {
        "total": total,
        "confirmadas": confirmadas,
        "pendientes": pendientes,
        "completadas": completadas,
        "appointments": sorted(appointments, key=lambda x: x.get("id", 0), reverse=True)
    }
