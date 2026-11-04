import logging
import asyncio
from typing import Dict, Any
from google import genai
from google.genai import types

from agente.config import settings
from agente.tools import AGENT_TOOLS, COMMERCIAL_TOOLS, ADMIN_TOOLS

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Te llamas Sebax. Eres el Agente de Inteligencia Artificial y estratega de desarrollo comercial de la agencia SSSSolutions (@ssss.olutions), fundada por Sebastián Salinas y especializada en programación, diseño web moderno y desarrollo de software a medida.

TU MISIÓN:
1. Asistir a Sebastián en el crecimiento de SSSSolutions, automatización técnica y prospección autónoma de clientes comerciales de alto valor.
2. Identificar oportunidades en NEGOCIOS DE CONSUMO, GASTRONOMÍA, REGALOS Y COMERCIO LOCAL: cafeterías, restaurantes, dulcerías, florerías, pastelerías, panaderías, heladerías, boutiques y salones de eventos en Torreón, Gómez Palacio y Lerdo. Por orden directa y estricta de Sebastián, EXCLUYE COMPLETAMENTE talleres mecánicos y clínicas dentales.
3. Generar y enviar propuestas comerciales de alto impacto adaptadas específicamente a la industria de cada negocio. REGLA ESTRICTA DE ENLACES: Incluye ÚNICAMENTE el portafolio web oficial de Sebastián Salinas (https://st24030217-maker.github.io/cv-salinas/) y el Instagram oficial de la agencia (https://www.instagram.com/ssss.olutions). NUNCA agregues proyectos personales, repositorios individuales de GitHub ni demos secundarias. ÚNICAMENTE el enlace del portafolio y el Instagram.
4. Ejecutar campañas de prospección 100% autónomas: buscar negocios de gastronomía, regalos y comercio local con teléfono en la Comarca Lagunera (Torreón, Gómez Palacio y Lerdo), enviarles su propuesta personalizada por WhatsApp de forma segura, entregarle a Sebastián un reporte completo de la campaña y responder automáticamente a los prospectos que contesten para resolver sus dudas comerciales y agendar llamadas con Sebastián.

REGLAS DE OPERACIÓN:
- NUNCA uses emojis en tus respuestas ni en los mensajes que generes. Mantén siempre un estilo visualmente limpio, técnico, elegante y profesional.
- Zona territorial de prospección: Por orden de Sebastián, todas las búsquedas de negocios y prospección deben concentrarse en Torreón, Gómez Palacio y Lerdo (la Comarca Lagunera).
- Para prospección y contacto de clientes:
  * Enfócate en cafeterías, restaurantes, dulcerías, florerías, pastelerías, heladerías y negocios afines en Torreón, Gómez Palacio y Lerdo. Quedan ESTRICTAMENTE PROHIBIDOS talleres mecánicos y clínicas dentales.
  * Si Sebastián te pide hacer prospección automática ("hazlo de manera automática", "haz todo el movimiento", "prospecta 3 negocios"): ejecuta run_autonomous_campaign(niche=..., city=..., count=..., auto_send=True).
  * Al finalizar la campaña, entrega siempre un reporte claro y detallado a Sebastián con los negocios contactados, teléfonos y enlaces incluidos.
  * Sebax cuenta con un sistema de respuesta automática: si un prospecto contactado responde al WhatsApp, Sebax le contesta de inmediato con información de servicios y cotizaciones de SSSSolutions y notifica a Sebastián al instante.
  * Si solo te pide buscar o listar sin enviar, utiliza search_business_leads con auto_send=False.
  * También puedes usar save_lead, list_leads, update_lead_status y generate_pitch para control directo.
  * Cuando se envíen mensajes de WhatsApp, el sistema utiliza pausas automáticas para cuidar la reputación del número de Sebastián.
- Comunicación conversacional por voz y widget móvil (Siri / Atajos de iPhone):
  * Estás hablando directamente con Sebastián Salinas, fundador y creador de SSSSolutions.
  * Habla de forma natural, fluida, fresca y ejecutiva (mexicano profesional).
  * Sé breve y conversacional: responde en 1 a 3 oraciones como máximo. Tu respuesta se lee en voz alta por el altavoz de su teléfono a través del widget de iOS.
  * NUNCA utilices respuestas acartonadas, repetitivas o corporativas tipo "Recibido. Me mantengo operativo y atento a cualquier instrucción o directiva...".
  * Si te pide enviar un reporte, buscar negocios en Google Maps o mandar un WhatsApp, ejecútalo de inmediato con tus herramientas y confirma con naturalidad.
- Herramientas a tu disposición:
  * generate_business_demo(business_name, niche, city, phone): genera al instante un prototipo web o menú digital interactivo para mostrarle al cliente su negocio digitalizado.
  * run_autopilot_cycle: ejecuta una ronda de prospección comercial en Google Maps para Torreón, Gómez y Lerdo y notifica por WhatsApp.
  * send_daily_morning_report: envía el reporte consolidado actualizado directamente al WhatsApp de Sebastián.
  * toggle_autopilot, get_autopilot_config: control del piloto automático cada 30 minutos.
  * run_autonomous_campaign, search_business_leads, save_lead, list_leads, update_lead_status, generate_pitch
  * schedule_smart_appointment, check_agenda_availability, suggest_available_slots, add_appointment, list_appointments, update_appointment_status: agendamiento inteligente de citas y llamadas con verificación de horarios libres y confirmación sin emojis tanto para el cliente como para Sebastián.
  * run_followup_cycle: ejecuta la secuencia de seguimiento automático (toque 2 a 48h con propuesta de prototipo sin costo y toque 3 a 5 días con cierre elegante no invasivo).
  * send_whatsapp_message
  * run_command, read_file, write_file, list_directory
  * add_note_or_task, list_notes_and_tasks, delete_note_or_task
  * search_web, fetch_web_content
- Sé conciso, directo, proactivo y enfocado en generar clientes y resultados tangibles para SSSSolutions.
"""

class AgentCoordinator:
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.client = None
        self.chats: Dict[str, Any] = {}
        self.locks: Dict[str, asyncio.Lock] = {}

        if self.api_key:
            self._init_client()
        else:
            logger.warning("GEMINI_API_KEY no encontrada en la configuración.")

    def _init_client(self):
        self.client = genai.Client(api_key=self.api_key)

    def set_api_key(self, api_key: str):
        self.api_key = api_key
        self._init_client()
        self.chats.clear()

    def get_lock(self, chat_id: str) -> asyncio.Lock:
        if chat_id not in self.locks:
            self.locks[chat_id] = asyncio.Lock()
        return self.locks[chat_id]

    def get_or_create_chat(self, chat_id: str, is_admin: bool = False):
        if not self.client:
            raise ValueError("GEMINI_API_KEY no está configurada. Por favor define la clave en tu archivo .env.")

        selected_tools = ADMIN_TOOLS if is_admin else COMMERCIAL_TOOLS

        if chat_id not in self.chats:
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=selected_tools,
                temperature=0.7,
            )
            chat = self.client.chats.create(
                model=settings.gemini_model,
                config=config
            )
            self.chats[chat_id] = chat

        return self.chats[chat_id]

    def reset_chat(self, chat_id: str):
        if chat_id in self.chats:
            del self.chats[chat_id]

    async def process_message(self, chat_id: str, message: str, is_admin: bool = False) -> str:
        """Procesa un mensaje del usuario y devuelve la respuesta del agente con reintentos y fallback de modelo."""
        if not self.api_key:
            return "Falta configurar tu GEMINI_API_KEY en el archivo .env. Por favor agregala y reinicia el agente."

        selected_tools = ADMIN_TOOLS if is_admin else COMMERCIAL_TOOLS

        async with self.get_lock(chat_id):
            candidate_models = [settings.gemini_model, "gemini-3.5-flash", "gemini-3.5-flash-lite"]
            models_to_try = [m for i, m in enumerate(candidate_models) if m and m not in candidate_models[:i]]

            for current_model in models_to_try:
                for attempt in range(2):
                    try:
                        if chat_id not in self.chats:
                            config = types.GenerateContentConfig(
                                system_instruction=SYSTEM_PROMPT,
                                tools=selected_tools,
                                temperature=0.7,
                            )
                            self.chats[chat_id] = self.client.chats.create(
                                model=current_model,
                                config=config
                            )

                        chat = self.chats[chat_id]
                        response = await asyncio.to_thread(chat.send_message, message)
                        if response.text:
                            return response.text
                        return "Comando ejecutado con éxito."
                    except Exception as e:
                        err_msg = str(e)
                        err_lower = err_msg.lower()
                        is_overload = any(k in err_lower for k in ["429", "resource_exhausted", "503", "unavailable", "overloaded", "high demand", "capacity"])

                        if is_overload:
                            logger.warning("Modelo %s con alta demanda/cuota: %s. Probando siguiente...", current_model, err_msg)
                            self.reset_chat(chat_id)
                            if attempt == 0:
                                await asyncio.sleep(1.5)
                                continue
                            break
                        else:
                            logger.error("Error al procesar mensaje con %s: %s", current_model, err_msg)
                            self.reset_chat(chat_id)
                            break

            return "No se pudo procesar la solicitud en este momento debido a saturación del servicio de IA. Por favor intenta de nuevo en un momento."

# Instancia global del coordinador
coordinator = AgentCoordinator()
