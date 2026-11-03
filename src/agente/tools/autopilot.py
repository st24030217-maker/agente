import asyncio
import json
import logging
import time
from datetime import datetime, date, timezone, timedelta
from pathlib import Path

from agente.config import DATA_DIR
from agente.tools.whatsapp import is_delivery_confirmed, is_delivery_pending, send_whatsapp_message
from agente.tools.agenda import _load_appointments
from agente.tools.prospecting import (
    discover_leads,
    generate_pitch,
    _load_leads,
    _save_leads,
    _is_excluded_business,
    DIVERSE_NICHES,
    PORTFOLIO_LINKS
)

logger = logging.getLogger(__name__)

# Zona horaria de la Comarca Lagunera (UTC-6)
LAGUNA_TZ = timezone(timedelta(hours=-6))

def get_laguna_now() -> datetime:
    """Devuelve la fecha y hora actual en la Comarca Lagunera."""
    return datetime.now(LAGUNA_TZ)

AUTOPILOT_FILE = DATA_DIR / "autopilot.json"

DEFAULT_CONFIG = {
    "enabled": True,
    "operate_hour": 8,          # Inicio de jornada (8:00 AM Hora Laguna)
    "end_hour": 21,             # Fin de jornada comercial (9:00 PM Hora Laguna)
    "report_hour": 9,           # Reporte matutino consolidado a las 9:00 AM
    "interval_minutes": 30,     # Búsqueda y envío cada 30 minutos
    "batch_size": 2,            # 2 negocios por ciclo (hasta 26 negocios al día)
    "target_cities": ["Torreón", "Gómez Palacio", "Ciudad Lerdo"],
    "last_run": None,
    "last_daily_date": None,
    "last_daily_run": None,
    "last_daily_report": None,
    "sent_today": 0,
    "current_niche_idx": 0
}

def get_autopilot_config() -> dict:
    if not AUTOPILOT_FILE.exists():
        save_autopilot_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(AUTOPILOT_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            # Asegurar claves por defecto
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_autopilot_config(cfg: dict):
    with open(AUTOPILOT_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def toggle_autopilot(enabled: bool = None) -> dict:
    """Activa o pausa el piloto automático 24/7 de Sebax."""
    cfg = get_autopilot_config()
    if enabled is None:
        cfg["enabled"] = not cfg.get("enabled", True)
    else:
        cfg["enabled"] = bool(enabled)
    save_autopilot_config(cfg)
    return cfg

def run_autopilot_cycle() -> dict:
    """Ejecuta una ronda de prospección comercial: toma prospectos pendientes de la base de datos o busca nuevos en Torreón, Gómez o Lerdo y les envía la propuesta por WhatsApp."""
    cfg = get_autopilot_config()
    if not cfg.get("enabled", True):
        return {"executed": False, "reason": "Piloto automático en pausa"}

    # Rotar de giro comercial en cada ciclo
    idx = cfg.get("current_niche_idx", 0) % len(DIVERSE_NICHES)
    niche = DIVERSE_NICHES[idx]
    cfg["current_niche_idx"] = idx + 1

    batch_size = cfg.get("batch_size", 3)
    city = "Torreón, Gómez Palacio y Lerdo"
    now_str = get_laguna_now().strftime("%Y-%m-%d %H:%M:%S")

    existing_leads = _load_leads()

    # 1. Priorizar prospectos no contactados ('nuevo') ya guardados en data/leads.json
    def _is_valid_lead(l: dict) -> bool:
        if l.get("status") != "nuevo":
            return False
        if not l.get("phone"):
            return False
        if _is_excluded_business(l.get("name", ""), l.get("niche", ""), l.get("notes", "")):
            return False
        return True

    eligible_leads = [l for l in existing_leads if _is_valid_lead(l)]

    # Intentar emparejar con el giro en turno
    niche_lower = niche.lower()
    matching_leads = [
        l for l in eligible_leads
        if any(w in (l.get("niche") or "").lower() for w in niche_lower.split() if len(w) > 3)
    ]

    selected_leads = matching_leads[:batch_size]
    # Si faltan para completar el lote, tomar de los otros giros permitidos
    if len(selected_leads) < batch_size:
        for l in eligible_leads:
            if l not in selected_leads and len(selected_leads) < batch_size:
                selected_leads.append(l)

    # 2. Si todavía faltan para completar el lote, descubrir nuevos negocios en la web
    remaining_needed = batch_size - len(selected_leads)
    if remaining_needed > 0:
        newly_discovered = discover_leads(niche=niche, city=city, max_leads=remaining_needed)
        for item in newly_discovered:
            if not _is_excluded_business(item.get("name", ""), item.get("niche", ""), item.get("notes", "")):
                lead_id = len(existing_leads) + 1
                item_niche = item.get("niche", niche)
                pitch = generate_pitch(business_name=item["name"], niche=item_niche)
                new_rec = {
                    "id": lead_id,
                    "name": item["name"],
                    "phone": item["phone"],
                    "city": item.get("city", "La Laguna"),
                    "niche": item_niche,
                    "source": item.get("source", ""),
                    "notes": item.get("notes", "Descubierto en prospección web"),
                    "created_at": now_str,
                    "pitch": pitch,
                    "status": "nuevo"
                }
                existing_leads.append(new_rec)
                selected_leads.append(new_rec)

    if not selected_leads:
        cfg["last_run"] = now_str
        save_autopilot_config(cfg)
        return {"executed": True, "sent": 0, "niche": niche, "message": "No hay prospectos pendientes para contactar"}

    contacted_count = 0
    results = []

    for item in selected_leads:
        item_niche = item.get("niche", niche)
        pitch = item.get("pitch")
        if not pitch:
            pitch = generate_pitch(business_name=item["name"], niche=item_niche)
            item["pitch"] = pitch

        send_result = send_whatsapp_message(to_number=item["phone"], message=pitch)
        if is_delivery_confirmed(send_result):
            item["status"] = "contactado"
            item["contacted_at"] = now_str
            contacted_count += 1
            results.append(f"{item['name']} ({item['phone']}) [{item_niche}]")
        elif is_delivery_pending(send_result):
            item["status"] = "pendiente_confirmacion"
            item["notes"] = (item.get("notes", "") + f" | Entrega pendiente de confirmación: {send_result}").strip(" | ")
        else:
            item["status"] = "error_envio"
            item["notes"] = (item.get("notes", "") + f" | Error envio: {send_result}").strip(" | ")

        # Guardar inmediatamente tras cada envío para persistencia garantizada
        _save_leads(existing_leads)

        # Espaciado de seguridad anti-ban entre mensajes (10-15s)
        if len(selected_leads) > 1:
            time.sleep(12)

    cfg["last_run"] = now_str
    cfg["sent_today"] = cfg.get("sent_today", 0) + contacted_count
    save_autopilot_config(cfg)

    # Notificar inmediatamente a Sebastián a su WhatsApp personal (8719164677) sobre el ciclo de 30 min
    if contacted_count > 0:
        batch_summary_lines = "\n".join([f"• {b}" for b in results])
        batch_notice = (
            f"SEBAX - REPORTE DE CICLO (CADA 30 MIN)\n\n"
            f"Giro: {niche.title()}\n"
            f"Negocios contactados ({contacted_count}):\n"
            f"{batch_summary_lines}\n\n"
            f"Enlaces enviados: Portafolio e Instagram.\n"
            f"Total acumulado hoy: {cfg.get('sent_today', 0)}\n\n"
            f"Próxima búsqueda en 30 minutos."
        )
        try:
            send_whatsapp_message(to_number="8719164677", message=batch_notice)
        except Exception as e:
            logger.warning("Fallo al enviar notificación de lote a Sebastián: %s", e)
    else:
        cycle_notice = (
            f"SEBAX - REPORTE DE CICLO (CADA 30 MIN)\n\n"
            f"Giro explorado: {niche.title()}\n"
            f"Resultado: No se detectaron números nuevos sin contactar en este turno.\n"
            f"Total acumulado hoy: {cfg.get('sent_today', 0)}\n\n"
            f"Próxima búsqueda en 30 minutos."
        )
        try:
            send_whatsapp_message(to_number="8719164677", message=cycle_notice)
        except Exception as e:
            logger.warning("Fallo al enviar notificación de ciclo a Sebastián: %s", e)

    logger.info("Piloto automático completó ciclo: %d contactados en giro [%s]", contacted_count, niche)
    return {
        "executed": True,
        "sent": contacted_count,
        "niche": niche,
        "businesses": results
    }

def send_daily_morning_report() -> str:
    """Compila y envía el reporte diario consolidado al WhatsApp personal de Sebastián Salinas."""
    today_str = get_laguna_now().strftime("%Y-%m-%d")
    leads = _load_leads()
    appointments = _load_appointments()

    # Contar prospectos contactados hoy o en últimas 24 horas
    today_contacted = [l for l in leads if (l.get("contacted_at") or "").startswith(today_str)]
    replied_leads = [l for l in leads if l.get("status") == "respondio"]
    today_appointments = [a for a in appointments if (a.get("created_at") or "").startswith(today_str)]

    # Construir lista de próximas citas
    pending_appointments = [a for a in appointments if a.get("status") in ["confirmada", "en_negociacion"]]
    if pending_appointments:
        citas_lines = []
        for a in pending_appointments[-5:]:
            citas_lines.append(f"• [{a.get('status', '').upper()}] {a['business_name']} ({a.get('client_name', '')}) | Fecha: {a.get('date_time', 'Por acordar')} | Tel: {a.get('phone', '')}")
        citas_text = "\n".join(citas_lines)
    else:
        citas_text = "No hay citas pendientes agendadas en este momento."

    cfg = get_autopilot_config()
    total_sent_metric = len(today_contacted) if today_contacted else cfg.get("sent_today", 0)

    report = (
        f"REPORTE DIARIO DE SEBAX - SSSSOLUTIONS\n\n"
        f"Fecha: {today_str}\n"
        f"Estado: Sebax activo 24/7 en Torreón, Gómez Palacio y Lerdo\n\n"
        f"Resumen comercial de las últimas 24 horas:\n"
        f"• Negocios contactados: {total_sent_metric}\n"
        f"• Respuestas atendidas automáticamente: {len(replied_leads)}\n"
        f"• Citas y reuniones en agenda: {len(appointments)}\n\n"
        f"Enlaces enviados en cada propuesta:\n"
        f"• Portafolio: https://st24030217-maker.github.io/cv-salinas/\n"
        f"• Instagram: https://www.instagram.com/ssss.olutions\n\n"
        f"Próximas citas en agenda:\n"
        f"{citas_text}\n\n"
        f"Sebax continúa operando en segundo plano atendiendo respuestas y prospectando constantemente."
    )

    try:
        send_whatsapp_message(to_number="8719164677", message=report)
        cfg["last_daily_report"] = today_str
        save_autopilot_config(cfg)
        logger.info("Reporte diario matutino enviado exitosamente a Sebastián.")
        return report
    except Exception as e:
        logger.error("Error al enviar reporte diario a Sebastián: %s", e)
        return f"Error al enviar reporte: {e}"

def retry_unsent_leads() -> dict:
    """Reintenta el envío a todos los prospectos con estado 'error_envio'."""
    leads = _load_leads()
    failed_leads = [l for l in leads if l.get("status") == "error_envio"]
    if not failed_leads:
        return {"executed": True, "retried": 0, "message": "No hay prospectos pendientes"}

    retried_count = 0
    now_str = get_laguna_now().strftime("%Y-%m-%d %H:%M:%S")
    for item in failed_leads:
        phone = item.get("phone")
        pitch = item.get("pitch")
        if not phone or not pitch:
            continue
        res = send_whatsapp_message(to_number=phone, message=pitch)
        if is_delivery_confirmed(res):
            item["status"] = "contactado"
            item["contacted_at"] = now_str
            item["notes"] = (item.get("notes", "") + f" | Reintento exitoso: {now_str}").strip()
            retried_count += 1
            time.sleep(10)
        elif is_delivery_pending(res):
            item["status"] = "pendiente_confirmacion"
            item["notes"] = (item.get("notes", "") + f" | Entrega pendiente de confirmación: {res}").strip()
        else:
            item["notes"] = (item.get("notes", "") + f" | Error reintento: {res}").strip()
            if "conectado" in res.lower() or "connect" in res.lower():
                break

    _save_leads(leads)
    return {
        "executed": True,
        "retried": retried_count,
        "total_pending": len(failed_leads),
        "message": f"Se enviaron con éxito {retried_count} de {len(failed_leads)} prospectos pendientes."
    }

async def autopilot_background_worker():
    """Bucle permanente de piloto automático programado: prospección cada 30 minutos y reporte diario a Sebastián."""
    logger.info("Iniciando trabajador programado de Sebax (Prospección cada 30 min / Reporte Diario a 8719164677)...")
    await asyncio.sleep(15)

    while True:
        try:
            cfg = get_autopilot_config()
            now = get_laguna_now()
            today_str = now.strftime("%Y-%m-%d")

            if cfg.get("enabled", True):
                interval_minutes = cfg.get("interval_minutes", 30)

                # Reset de contador diario al cambiar de fecha
                if cfg.get("last_daily_date") != today_str:
                    cfg["last_daily_date"] = today_str
                    cfg["sent_today"] = 0
                    save_autopilot_config(cfg)

                # 1. Verificar si corresponde ejecutar el ciclo de cada 30 min
                last_run_str = cfg.get("last_run")
                should_run = False

                if not last_run_str:
                    should_run = True
                else:
                    try:
                        last_dt = datetime.strptime(last_run_str, "%Y-%m-%d %H:%M:%S")
                        elapsed_min = (now.replace(tzinfo=None) - last_dt).total_seconds() / 60
                        if elapsed_min >= interval_minutes:
                            should_run = True
                    except Exception:
                        should_run = True

                # Operar durante horario comercial de La Laguna (08:00 AM a 09:00 PM)
                start_h = cfg.get("operate_hour", 8)
                end_h = cfg.get("end_hour", 21)
                is_active_hours = start_h <= now.hour < end_h

                if should_run and is_active_hours:
                    logger.info("Ciclo de prospección (cada 30 min): ejecutando búsqueda y contacto en La Laguna...")
                    await asyncio.to_thread(retry_unsent_leads)
                    await asyncio.to_thread(run_autopilot_cycle)

                # 2. Envío de Reporte Consolidado Matutino Diario (09:00 AM Hora de La Laguna a 8719164677)
                report_hour = cfg.get("report_hour", 9)
                if now.hour >= report_hour and cfg.get("last_daily_report") != today_str:
                    logger.info("09:00 AM alcanzada: Enviando reporte ejecutivo matutino al WhatsApp 8719164677...")
                    await asyncio.to_thread(send_daily_morning_report)
                    cfg = get_autopilot_config()
                    cfg["last_daily_report"] = today_str
                    save_autopilot_config(cfg)

        except Exception as e:
            logger.error("Error en bucle de piloto automático programado: %s", e)

        # Verificar cada 60 segundos
        await asyncio.sleep(60)
