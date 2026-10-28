import asyncio
import json
import logging
import time
from datetime import datetime, date
from pathlib import Path

from agente.config import DATA_DIR
from agente.tools.whatsapp import send_whatsapp_message
from agente.tools.agenda import _load_appointments
from agente.tools.prospecting import (
    discover_leads,
    generate_pitch,
    _load_leads,
    _save_leads,
    DIVERSE_NICHES,
    PORTFOLIO_LINKS
)

logger = logging.getLogger(__name__)

AUTOPILOT_FILE = DATA_DIR / "autopilot.json"

DEFAULT_CONFIG = {
    "enabled": True,
    "interval_minutes": 25,
    "batch_size": 2,
    "target_cities": ["Torreón", "Gómez Palacio", "Ciudad Lerdo"],
    "last_run": None,
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
    """Ejecuta una ronda de prospección continua: busca negocios en Torreón, Gómez o Lerdo y les envía la propuesta por WhatsApp."""
    cfg = get_autopilot_config()
    if not cfg.get("enabled", True):
        return {"executed": False, "reason": "Piloto automático en pausa"}

    # Rotar de giro comercial en cada ciclo
    idx = cfg.get("current_niche_idx", 0) % len(DIVERSE_NICHES)
    niche = DIVERSE_NICHES[idx]
    cfg["current_niche_idx"] = idx + 1

    batch_size = cfg.get("batch_size", 2)
    city = "Torreón, Gómez Palacio y Lerdo"

    leads_found = discover_leads(niche=niche, city=city, max_leads=batch_size)
    if not leads_found:
        cfg["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_autopilot_config(cfg)
        return {"executed": True, "sent": 0, "niche": niche, "message": "No se detectaron prospectos nuevos en este ciclo"}

    existing_leads = _load_leads()
    contacted_count = 0
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results = []

    for item in leads_found:
        lead_id = len(existing_leads) + 1
        item_niche = item.get("niche", niche)
        pitch = generate_pitch(business_name=item["name"], niche=item_niche)

        lead_record = {
            "id": lead_id,
            "name": item["name"],
            "phone": item["phone"],
            "city": item.get("city", "La Laguna"),
            "niche": item_niche,
            "source": item.get("source", ""),
            "notes": item.get("notes", "Contactado por piloto automático 24/7"),
            "created_at": now_str,
            "pitch": pitch,
            "status": "nuevo"
        }

        send_result = send_whatsapp_message(to_number=item["phone"], message=pitch)
        if "éxito" in send_result.lower() or "success" in send_result.lower():
            lead_record["status"] = "contactado"
            lead_record["contacted_at"] = now_str
            contacted_count += 1
            results.append(f"{item['name']} ({item['phone']}) [{item_niche}]")
        else:
            lead_record["status"] = "error_envio"
            lead_record["notes"] += f" | Error envio: {send_result}"

        existing_leads.append(lead_record)

        # Espaciado de seguridad entre mensajes
        if len(leads_found) > 1:
            time.sleep(10)

    _save_leads(existing_leads)

    cfg["last_run"] = now_str
    cfg["sent_today"] = cfg.get("sent_today", 0) + contacted_count
    save_autopilot_config(cfg)

    logger.info("Piloto automático completó ciclo: %d contactados en giro [%s]", contacted_count, niche)
    return {
        "executed": True,
        "sent": contacted_count,
        "niche": niche,
        "businesses": results
    }

def send_daily_morning_report() -> str:
    """Compila y envía el reporte diario consolidado al WhatsApp personal de Sebastián Salinas."""
    today_str = datetime.now().strftime("%Y-%m-%d")
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
        send_whatsapp_message(to_number="self", message=report)
        cfg["last_daily_report"] = today_str
        cfg["sent_today"] = 0  # Reiniciar contador para el nuevo día
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
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for item in failed_leads:
        phone = item.get("phone")
        pitch = item.get("pitch")
        if not phone or not pitch:
            continue
        res = send_whatsapp_message(to_number=phone, message=pitch)
        if "éxito" in res.lower() or "success" in res.lower():
            item["status"] = "contactado"
            item["contacted_at"] = now_str
            item["notes"] = (item.get("notes", "") + f" | Reintento exitoso: {now_str}").strip()
            retried_count += 1
            time.sleep(10)
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
    """Bucle asíncrono permanente de piloto automático que corre 24/7 en segundo plano."""
    logger.info("Iniciando trabajador 24/7 de Piloto Automático Sebax...")
    # Esperar 40 segundos al arranque para permitir que los puentes se estabilicen
    await asyncio.sleep(40)

    while True:
        try:
            cfg = get_autopilot_config()
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")

            # 1. Verificar si corresponde enviar el reporte matutino (09:00 AM o primera hora del día)
            if now.hour >= 9 and cfg.get("last_daily_report") != today_str:
                await asyncio.to_thread(send_daily_morning_report)

            # 2. Verificar ciclo de prospección automática
            if cfg.get("enabled", True):
                last_run_str = cfg.get("last_run")
                should_run = False

                if not last_run_str:
                    should_run = True
                else:
                    try:
                        last_run_dt = datetime.strptime(last_run_str, "%Y-%m-%d %H:%M:%S")
                        diff_minutes = (now - last_run_dt).total_seconds() / 60
                        if diff_minutes >= cfg.get("interval_minutes", 25):
                            should_run = True
                    except Exception:
                        should_run = True

                if should_run:
                    logger.info("Ejecutando ciclo automático de prospección 24/7...")
                    await asyncio.to_thread(retry_unsent_leads)
                    await asyncio.to_thread(run_autopilot_cycle)

        except Exception as e:
            logger.error("Error en bucle de piloto automático: %s", e)

        # Dormir 60 segundos antes de la siguiente verificación
        await asyncio.sleep(60)
