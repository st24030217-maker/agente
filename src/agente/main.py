import sys
import re
import asyncio
import logging
import httpx
from datetime import datetime
from pathlib import Path
import uvicorn
import edge_tts
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agente.config import settings, BASE_DIR
from agente.agent import coordinator
from agente.tools.prospecting import (
    get_leads_stats,
    run_autonomous_campaign,
    update_lead_status,
    generate_lead_reply,
    _load_leads,
    _save_leads,
    normalize_mx_phone
)
from agente.tools.whatsapp import send_whatsapp_message
from agente.tools.agenda import (
    add_appointment,
    list_appointments,
    update_appointment_status,
    get_appointments_stats
)
from agente.tools.autopilot import (
    autopilot_background_worker,
    get_autopilot_config,
    toggle_autopilot,
    run_autopilot_cycle,
    send_daily_morning_report,
    retry_unsent_leads
)
from agente.tools.demo_generator import (
    generate_business_demo,
    get_demo,
    list_all_demos,
    render_demo_html
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("agente")

app = FastAPI(title="Sebax - AI Personal Agent", version="1.0.0")

STATIC_DIR = Path(__file__).resolve().parent / "static"

class WhatsAppWebhookRequest(BaseModel):
    sender: str
    message: str

class WhatsAppWebhookResponse(BaseModel):
    reply: str

class DirectChatRequest(BaseModel):
    message: str
    chat_id: str = "cli_default"

class CampaignRequest(BaseModel):
    niche: str = "Cualquier negocio"
    city: str = "Torreón, Gómez Palacio y Lerdo"
    count: int = 3
    auto_send: bool = True

class LeadSendRequest(BaseModel):
    phone: str
    message: str
    lead_id: int | None = None

class LeadIncomingCheck(BaseModel):
    sender: str
    message: str = ""

class AppointmentCreateRequest(BaseModel):
    business_name: str
    client_name: str = ""
    phone: str = ""
    date_time: str = ""
    notes: str = ""
    status: str = "confirmada"

class AppointmentUpdateRequest(BaseModel):
    appointment_id: int
    status: str
    notes: str = ""

class AutopilotToggleRequest(BaseModel):
    enabled: bool | None = None

class DemoCreateRequest(BaseModel):
    business_name: str
    niche: str = "cafeteria"
    city: str = "Torreón, Coahuila"
    phone: str = ""
    custom_tagline: str = ""

@app.get("/health")
def health_check():
    return {
        "status": "online",
        "gemini_model": settings.gemini_model,
        "api_key_configured": bool(settings.gemini_api_key),
        "allowed_numbers": settings.allowed_numbers,
        "workspace": settings.workspace_dir
    }

@app.get("/webhook/whatsapp")
@app.get("/api/webhook/whatsapp")
async def verify_meta_webhook(request: Request):
    """Verificación oficial requerida por Meta para registrar el Webhook de WhatsApp Cloud API."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    verify_token = settings.meta_wa_verify_token or "sebax_ssssolutions_2026"
    if mode == "subscribe" and token == verify_token:
        logger.info("Meta WhatsApp Cloud Webhook verificado con éxito.")
        return Response(content=challenge, media_type="text/plain")

    logger.warning("Verificación de Webhook de Meta rechazada por token inválido.")
    return Response(content="Forbidden", status_code=403)

@app.post("/webhook/whatsapp")
@app.post("/api/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """Receptor unificado para Meta WhatsApp Cloud API y el conector Baileys."""
    try:
        data = await request.json()
    except Exception:
        return Response(content="Invalid JSON", status_code=400)

    # 1. Caso: Evento oficial de Meta WhatsApp Cloud API
    if "object" in data and "entry" in data:
        try:
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    for msg in messages:
                        if msg.get("type") == "text":
                            sender = msg.get("from", "")
                            text_body = msg.get("text", {}).get("body", "").strip()
                            if sender and text_body:
                                logger.info("Meta WA Cloud recibido de [%s]: %s", sender, text_body)
                                if text_body.lower() in ["/reset", "/reiniciar", "/clear"]:
                                    coordinator.reset_chat(sender)
                                    send_whatsapp_message(to_number=sender, message="Conversación y contexto reiniciados exitosamente.")
                                else:
                                    reply = await coordinator.process_message(chat_id=sender, message=text_body)
                                    if reply:
                                        send_whatsapp_message(to_number=sender, message=reply)
        except Exception as e:
            logger.error("Error al procesar evento de Meta WhatsApp Cloud: %s", e)
        return Response(content="EVENT_RECEIVED", status_code=200)

    # 2. Caso: Puente Baileys local
    sender = str(data.get("sender", "")).strip()
    message = str(data.get("message", "")).strip()

    if not sender or not message:
        return {"reply": ""}

    logger.info("Mensaje Baileys recibido de [%s]: %s", sender, message)

    is_self = sender.lower() in ["self", "self_user", "yo", "mismo"]
    if settings.allowed_numbers and not is_self:
        sender_digits = "".join(filter(str.isdigit, sender))
        is_allowed = any(
            "".join(filter(str.isdigit, allowed)) in sender_digits
            for allowed in settings.allowed_numbers
        )
        if not is_allowed:
            logger.warning("Mensaje ignorado del remitente no autorizado: %s", sender)
            return {"reply": ""}

    if message.lower() in ["/reset", "/reiniciar", "/clear"]:
        coordinator.reset_chat(sender)
        return {"reply": "Conversacion y contexto reiniciados exitosamente."}

    reply = await coordinator.process_message(chat_id=sender, message=message, is_admin=is_self)
    return {"reply": reply}

@app.post("/chat")
@app.post("/api/chat")
async def chat_direct(payload: DirectChatRequest):
    reply = await coordinator.process_message(chat_id=payload.chat_id, message=payload.message, is_admin=False)
    return {"reply": reply}

@app.get("/demo/{slug}", response_class=Response)
async def view_demo(slug: str):
    """Visualizador público del prototipo web interactivo generado para el prospecto."""
    demo = get_demo(slug)
    if not demo:
        clean_name = slug.replace("-", " ").title()
        demo_res = generate_business_demo(business_name=clean_name, niche="cafeteria", city="Torreón, Coahuila")
        demo = get_demo(demo_res["slug"])
    html_content = render_demo_html(demo)
    return Response(content=html_content, media_type="text/html")

@app.get("/api/demos")
def get_demos_api():
    """Listado de todos los prototipos comerciales generados."""
    return list_all_demos()

@app.post("/api/demos/create")
def create_demo_api(payload: DemoCreateRequest):
    """Crea un prototipo interactivo para un negocio específico."""
    return generate_business_demo(
        business_name=payload.business_name,
        niche=payload.niche,
        city=payload.city,
        phone=payload.phone,
        custom_tagline=payload.custom_tagline
    )

@app.get("/qr")
async def get_qr_page():
    """Proxy para mostrar el código QR de vinculación de WhatsApp directamente en el navegador."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"http://127.0.0.1:{settings.bridge_port}/qr", timeout=10.0)
            return Response(content=resp.content, media_type="text/html")
        except Exception as e:
            return Response(content=f"<div style='font-family:sans-serif;text-align:center;padding:40px;'><h3>Iniciando puente de WhatsApp...</h3><p>{e}</p></div>", media_type="text/html")

@app.get("/api/bridge/status")
async def get_bridge_status():
    """Estado de conexión del conector de WhatsApp."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"http://127.0.0.1:{settings.bridge_port}/status", timeout=5.0)
            return resp.json()
        except Exception:
            return {"status": "starting"}

@app.get("/qr-data")
async def get_qr_data_proxy():
    """Proxy para datos del QR en tiempo real."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"http://127.0.0.1:{settings.bridge_port}/qr-data", timeout=5.0)
            return resp.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}

@app.post("/pairing-code")
@app.post("/api/bridge/pairing-code")
async def post_pairing_code_proxy(request: Request):
    """Proxy para solicitar código de vinculación de 8 dígitos."""
    body = await request.json()
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"http://127.0.0.1:{settings.bridge_port}/pairing-code",
                json=body,
                timeout=15.0
            )
            return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")
        except Exception as e:
            return Response(content=json.dumps({"error": str(e)}), status_code=500, media_type="application/json")

@app.post("/api/bridge/reset")
async def post_bridge_reset():
    """Reinicia la sesión del puente de WhatsApp para generar un nuevo código."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"http://127.0.0.1:{settings.bridge_port}/reset", timeout=10.0)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

@app.get("/api/status")
def api_status():
    return {
        "status": "online",
        "agent": "Sebax",
        "model": settings.gemini_model,
        "whatsapp_connected": True
    }

@app.get("/api/leads")
def get_leads_api():
    """Devuelve la lista completa de prospectos y métricas de prospección."""
    return get_leads_stats()

@app.post("/api/leads/campaign")
async def run_campaign_api(payload: CampaignRequest):
    """Ejecuta una campaña de prospección y envío en segundo plano."""
    try:
        summary = await asyncio.to_thread(
            run_autonomous_campaign,
            niche=payload.niche,
            city=payload.city,
            count=payload.count,
            auto_send=payload.auto_send
        )
        stats = get_leads_stats()
        return {"success": True, "summary": summary, "stats": stats}
    except Exception as e:
        logger.error("Error al ejecutar campaña desde API: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/leads/send")
async def send_lead_pitch_api(payload: LeadSendRequest):
    """Envía una propuesta personalizada a un prospecto específico."""
    result = await asyncio.to_thread(send_whatsapp_message, to_number=payload.phone, message=payload.message)
    if payload.lead_id:
        update_lead_status(payload.lead_id, "contactado", f"Mensaje enviado individualmente: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    return {"result": result}

@app.post("/api/leads/incoming")
async def check_incoming_lead_api(payload: LeadIncomingCheck):
    """Verifica si un mensaje entrante proviene de un prospecto de negocios, responde automáticamente y notifica a Sebastián."""
    sender_digits = re.sub(r"\D", "", payload.sender)
    leads = _load_leads()
    matched_lead = None

    for l in leads:
        lead_digits = re.sub(r"\D", "", l.get("phone", ""))
        if (lead_digits and sender_digits.endswith(lead_digits[-10:])) or (sender_digits and lead_digits.endswith(sender_digits[-10:])):
            matched_lead = l
            break

    if matched_lead:
        matched_lead["status"] = "respondio"
        matched_lead["last_reply"] = payload.message
        matched_lead["last_reply_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Detectar si el prospecto propone o solicita agendar una cita o llamada
        msg_lower = payload.message.lower()
        if any(w in msg_lower for w in ["cita", "llamada", "reunion", "agendar", "mañana", "hora", "vernos", "platicar", "reunirnos", "zoom"]):
            try:
                add_appointment(
                    business_name=matched_lead.get("name", "Prospecto"),
                    client_name=matched_lead.get("name", "Contacto"),
                    phone=matched_lead.get("phone", ""),
                    date_time="Por confirmar con el cliente",
                    notes=f"Solicitud automática recibida por WhatsApp: '{payload.message}'",
                    status="en_negociacion"
                )
            except Exception as e:
                logger.warning("Fallo al registrar cita automática: %s", e)

        # Generar respuesta automática con Sebax para el prospecto
        ai_reply = await generate_lead_reply(
            lead_name=matched_lead.get("name", "Cliente"),
            lead_niche=matched_lead.get("niche", "negocio"),
            incoming_message=payload.message
        )

        matched_lead["last_agent_reply"] = ai_reply
        _save_leads(leads)

        # Notificar en tiempo real al chat personal de Sebastián con el reporte de la interacción
        notice = (
            f"AVISO DE PROSPECTO EN WHATSAPP\n\n"
            f"El negocio '{matched_lead['name']}' (+{matched_lead['phone']}) ha respondido:\n"
            f"\"{payload.message}\"\n\n"
            f"Sebax le respondió automáticamente:\n"
            f"\"{ai_reply}\"\n\n"
            f"Giro: {matched_lead.get('niche', 'general')} | Ciudad: {matched_lead.get('city', '')}\n"
            f"Puedes continuar la conversación con el cliente cuando lo desees."
        )
        try:
            await asyncio.to_thread(send_whatsapp_message, to_number="self", message=notice)
        except Exception as e:
            logger.warning("Fallo al enviar aviso de lead entrante: %s", e)

        return {"is_lead": True, "reply": ai_reply, "lead": matched_lead}

    return {"is_lead": False}

@app.get("/api/autopilot")
def get_autopilot_api():
    """Devuelve la configuración y estado actual del piloto automático 24/7."""
    return get_autopilot_config()

@app.post("/api/autopilot/toggle")
def toggle_autopilot_api(payload: AutopilotToggleRequest):
    """Activa o pausa el piloto automático 24/7."""
    return toggle_autopilot(payload.enabled)

@app.post("/api/autopilot/run")
async def run_autopilot_now_api():
    """Ejecuta inmediatamente un ciclo de prospección automática en Torreón, Gómez y Lerdo."""
    res = await asyncio.to_thread(run_autopilot_cycle)
    return res

@app.post("/api/autopilot/report")
async def send_autopilot_report_api():
    """Compila y envía el reporte diario consolidado al WhatsApp personal de Sebastián Salinas."""
    report = await asyncio.to_thread(send_daily_morning_report)
    return {"success": True, "report": report}

@app.post("/api/autopilot/retry")
async def retry_autopilot_leads_api():
    """Reintenta el envío de mensajes a prospectos pendientes con error de envío."""
    res = await asyncio.to_thread(retry_unsent_leads)
    return res

@app.get("/api/appointments")
def get_appointments_api():
    """Devuelve las citas agendadas y estadísticas para la agenda."""
    return get_appointments_stats()

@app.post("/api/appointments")
def create_appointment_api(payload: AppointmentCreateRequest):
    """Crea una nueva cita o reunión agendada."""
    result = add_appointment(
        business_name=payload.business_name,
        client_name=payload.client_name,
        phone=payload.phone,
        date_time=payload.date_time,
        notes=payload.notes,
        status=payload.status
    )
    return {"success": True, "result": result, "stats": get_appointments_stats()}

@app.put("/api/appointments")
def update_appointment_api(payload: AppointmentUpdateRequest):
    """Actualiza el estado de una cita."""
    result = update_appointment_status(
        appointment_id=payload.appointment_id,
        status=payload.status,
        notes=payload.notes
    )
    return {"success": True, "result": result, "stats": get_appointments_stats()}

@app.get("/api/tts")
async def get_tts(text: str, voice: str = "es-MX-JorgeNeural"):
    """Genera audio con voz neuronal humana ultrarrealista con tolerancia a fallos."""
    clean_text = re.sub(r'[*_#`~]', '', text).strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Texto vacío")
    if len(clean_text) > 400:
        clean_text = clean_text[:400]

    voices_to_try = [voice, "es-MX-JorgeNeural", "es-MX-PelayoNeural", "es-ES-AlvaroNeural"]
    unique_voices = list(dict.fromkeys(voices_to_try))

    for v in unique_voices:
        try:
            communicate = edge_tts.Communicate(clean_text, voice=v)
            audio_data = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data.extend(chunk["data"])
            if len(audio_data) > 0:
                return Response(content=bytes(audio_data), media_type="audio/mpeg")
        except Exception as e:
            logger.warning("Fallo al generar TTS con voz %s: %s", v, e)
            continue

    raise HTTPException(status_code=500, detail="No se pudo sintetizar audio en este momento.")

@app.on_event("startup")
async def startup_event():
    """Inicia tareas de fondo: keep-alive y el piloto automático 24/7 de prospección continua."""
    asyncio.create_task(render_keepalive_loop())
    asyncio.create_task(autopilot_background_worker())

async def render_keepalive_loop():
    """Envía un ping periódico al endpoint health para evitar la suspensión en Render free tier."""
    await asyncio.sleep(60)
    health_url = "https://agente-hgba.onrender.com/health"
    while True:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.get(health_url)
                logger.debug("Render keepalive ping enviado.")
        except Exception:
            pass
        await asyncio.sleep(600) # Ping cada 10 minutos

# Montar interfaz web interactiva con el Avatar 3D
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

async def run_cli_interactive():
    print("\n=======================================================")
    print("Sebax - Agente de Inteligencia Artificial para SSSSolutions")
    print("Escribe tus mensajes o comandos. Escribe 'exit' para salir.")
    print("=======================================================\n")
    chat_id = "local_dev"
    while True:
        try:
            user_input = input("\n[Tu] > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "salir"]:
                print("Hasta luego.")
                break
            if user_input.lower() in ["/reset", "/clear"]:
                coordinator.reset_chat(chat_id)
                print("Contexto reiniciado.")
                continue

            print("Sebax procesando...")
            reply = await coordinator.process_message(chat_id=chat_id, message=user_input)
            print(f"\n[Sebax]:\n{reply}")
        except (KeyboardInterrupt, EOFError):
            print("\nSaliendo...")
            break

def start():
    if "--cli" in sys.argv:
        asyncio.run(run_cli_interactive())
    else:
        uvicorn.run(
            "agente.main:app",
            host=settings.server_host,
            port=settings.server_port,
            reload=False
        )

if __name__ == "__main__":
    start()
