import logging
import asyncio
from typing import Dict, Any
from google import genai
from google.genai import types

from agente.config import settings
from agente.tools import AGENT_TOOLS

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
- Herramientas a tu disposición:
  * run_autonomous_campaign, search_business_leads, save_lead, list_leads, update_lead_status, generate_pitch
  * add_appointment, list_appointments, update_appointment_status: gestión completa de citas y reuniones de negocios para Sebastián.
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

    def get_or_create_chat(self, chat_id: str):
        if not self.client:
            raise ValueError("GEMINI_API_KEY no está configurada. Por favor define la clave en tu archivo .env.")

        if chat_id not in self.chats:
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=AGENT_TOOLS,
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

    async def process_message(self, chat_id: str, message: str) -> str:
        """Procesa un mensaje del usuario y devuelve la respuesta del agente con reintentos y fallback de modelo."""
        if not self.api_key:
            return "Falta configurar tu GEMINI_API_KEY en el archivo .env. Por favor agregala y reinicia el agente."

        async with self.get_lock(chat_id):
            candidate_models = [settings.gemini_model, "gemini-3.5-flash-lite"]
            # Asegurar modelos únicos
            models_to_try = list(dict.fromkeys(candidate_models))

            for current_model in models_to_try:
                for attempt in range(2):
                    try:
                        if chat_id not in self.chats:
                            config = types.GenerateContentConfig(
                                system_instruction=SYSTEM_PROMPT,
                                tools=AGENT_TOOLS,
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
                        # Si el chat se bloqueó o cambió de modelo, reiniciarlo
                        if "429" in err_msg or "resource_exhausted" in err_msg.lower():
                            logger.warning("Cuota alcanzada en modelo %s. Intentando modelo de respaldo...", current_model)
                            self.reset_chat(chat_id)
                            break  # Pasar al siguiente modelo de respaldo
                        elif ("503" in err_msg or "overloaded" in err_msg.lower()) and attempt == 0:
                            logger.warning("Modelo %s sobrecargado, reintentando en 2s...", current_model)
                            await asyncio.sleep(2.0)
                            continue
                        else:
                            self.reset_chat(chat_id)
                            break

            return "No se pudo procesar la solicitud en este momento debido a saturación del servicio de IA. Por favor intenta de nuevo en un momento."

# Instancia global del coordinador
coordinator = AgentCoordinator()
