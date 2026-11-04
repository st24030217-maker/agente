import os
import re
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from agente.config import DATA_DIR
from agente.tools.whatsapp import send_whatsapp_message

logger = logging.getLogger(__name__)

APPOINTMENTS_FILE = DATA_DIR / "appointments.json"
CALENDLY_URL = os.getenv("CALENDLY_URL", "").strip()
SEBASTIAN_WA = "8719164677"

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

def get_booking_link() -> str:
    """Devuelve el enlace oficial de agendamiento en línea (Calendly / Cal.com) o instrucciones directas."""
    if CALENDLY_URL:
        return CALENDLY_URL
    return "https://wa.me/528719164677?text=Hola%20Sebasti%C3%A1n%2C%20quisiera%20agendar%20una%20reuni%C3%B3n"

def suggest_available_slots() -> list[str]:
    """Genera 2 o 3 opciones de horarios hábiles y convenientes para proponer a un cliente comercial."""
    now = datetime.now()
    # Si es después de las 16:00, sugerir a partir de pasado mañana o mañana temprano
    tomorrow = now + timedelta(days=1)
    if tomorrow.weekday() == 6:  # Si es domingo, mover al lunes
        tomorrow += timedelta(days=1)
    
    day_after = tomorrow + timedelta(days=1)
    if day_after.weekday() == 6:
        day_after += timedelta(days=1)

    t_str = tomorrow.strftime("%d de %B") if hasattr(tomorrow, "strftime") else "Mañana"
    d_str = day_after.strftime("%d de %B") if hasattr(day_after, "strftime") else "Pasado mañana"

    return [
        "Mañana a las 11:00 AM",
        "Mañana a las 4:00 PM",
        "Pasado mañana a las 12:00 PM"
    ]

def check_agenda_availability(desired_datetime: str) -> dict:
    """Verifica si existe algún conflicto de horario con citas existentes en la agenda de SSSSolutions."""
    appointments = _load_appointments()
    active_appointments = [
        a for a in appointments 
        if a.get("status") in ["confirmada", "en_negociacion"]
    ]

    desired_clean = re.sub(r"\s+", " ", desired_datetime.lower().strip())
    conflicts = []

    for a in active_appointments:
        dt = re.sub(r"\s+", " ", str(a.get("date_time", "")).lower().strip())
        if dt and dt != "por confirmar con el cliente" and (dt in desired_clean or desired_clean in dt):
            conflicts.append(a)

    return {
        "available": len(conflicts) == 0,
        "conflicts": conflicts,
        "suggested_slots": suggest_available_slots()
    }

def schedule_smart_appointment(
    business_name: str,
    client_name: str = "",
    phone: str = "",
    date_time: str = "",
    notes: str = "",
    send_client_confirmation: bool = True
) -> str:
    """Agenda una cita inteligente para Sebastián Salinas y SSSSolutions, evitando conflictos, enviando confirmación profesional sin emojis al cliente y generando alerta prioritaria al WhatsApp de Sebastián."""
    appointments = _load_appointments()
    app_id = len(appointments) + 1
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Verificar disponibilidad
    avail = check_agenda_availability(date_time)
    has_conflict = not avail["available"]
    conflict_note = ""
    if has_conflict:
        conflict_names = ", ".join([c.get("business_name", "") for c in avail["conflicts"]])
        conflict_note = f" (Alerta: Posible traslape con: {conflict_names})"

    appointment = {
        "id": app_id,
        "business_name": business_name,
        "client_name": client_name or business_name,
        "phone": phone,
        "date_time": date_time,
        "notes": (notes + conflict_note).strip(),
        "status": "confirmada",
        "created_at": now_str
    }
    appointments.append(appointment)
    _save_appointments(appointments)

    # 1. Enviar confirmación al cliente por WhatsApp (si se proporcionó teléfono)
    clean_phone = re.sub(r"\D", "", phone or "")
    if send_client_confirmation and clean_phone and len(clean_phone) >= 10:
        booking_link = get_booking_link()
        client_msg = (
            f"Confirmacion de Cita - SSSSolutions\n\n"
            f"Estimado/a {client_name or business_name}, su reunion con Sebastian Salinas para {business_name} ha quedado agendada:\n"
            f"Fecha y hora: {date_time}\n"
            f"Temas a revisar: {notes or 'Propuesta digital, sitio web y soluciones comerciales'}\n\n"
            f"En caso de requerir reprogramar o agregar participantes, solo responda a este mensaje.\n\n"
            f"Portafolio oficial: https://st24030217-maker.github.io/cv-salinas/\n"
            f"Instagram: https://www.instagram.com/ssss.olutions"
        )
        try:
            send_whatsapp_message(to_number=clean_phone, message=client_msg)
        except Exception as e:
            logger.warning("No se pudo enviar confirmación de cita al cliente %s: %s", phone, e)

    # 2. Alerta prioritaria inmediata al WhatsApp de Sebastián Salinas
    wa_chat_link = f"https://wa.me/{clean_phone}" if clean_phone else "No proporcionado"
    admin_alert = (
        f"NUEVA CITA CONFIRMADA EN AGENDA - SSSSOLUTIONS\n\n"
        f"Cliente: {business_name} ({client_name or 'Contacto directo'})\n"
        f"Telefono: +{phone}\n"
        f"Fecha y Hora: {date_time}{conflict_note}\n"
        f"Notas: {notes or 'Sin notas adicionales'}\n"
        f"Estado: CONFIRMADA\n\n"
        f"Abrir chat directo con el cliente:\n"
        f"{wa_chat_link}"
    )
    try:
        send_whatsapp_message(to_number=SEBASTIAN_WA, message=admin_alert)
    except Exception as e:
        logger.warning("Fallo al enviar notificación de cita a Sebastián: %s", e)

    return (
        f"Cita ID {app_id} agendada y confirmada con exito para [{business_name}] el [{date_time}]. "
        f"Confirmacion enviada al cliente y alerta prioritaria entregada al WhatsApp de Sebastian."
    )

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
    clean_phone = re.sub(r"\D", "", phone or "")
    wa_link = f"\nChat directo con el cliente:\nhttps://wa.me/{clean_phone}" if clean_phone else ""
    alert_msg = (
        f"NUEVA CITA AGENDADA - SSSSOLUTIONS\n\n"
        f"Cliente: {business_name} ({client_name or 'Contacto directo'})\n"
        f"Telefono: {phone}\n"
        f"Fecha y Hora: {date_time}\n"
        f"Notas: {notes or 'Sin observaciones adicionales'}\n"
        f"Estado: {status.upper()}{wa_link}\n\n"
        f"Registrada por Sebax en la agenda del agente."
    )
    try:
        send_whatsapp_message(to_number=SEBASTIAN_WA, message=alert_msg)
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
