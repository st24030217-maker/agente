import json
import re
import time
import logging
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
import httpx
from ddgs import DDGS

from agente.config import DATA_DIR
from agente.tools.whatsapp import is_delivery_confirmed, is_delivery_pending, send_whatsapp_message

logger = logging.getLogger(__name__)

LEADS_FILE = DATA_DIR / "leads.json"

PORTFOLIO_LINKS = {
    "portfolio": "https://st24030217-maker.github.io/cv-salinas/",
    "instagram": "https://www.instagram.com/ssss.olutions"
}

# Giros comerciales enfocados en gastronomia, retail, regalos y consumo local
DIVERSE_NICHES = [
    "cafeterias y coffee shops",
    "restaurantes y comida",
    "dulcerias y confiterias",
    "florerias y arreglos florales",
    "pastelerias y reposteria",
    "panaderias artesanales",
    "neverias y heladerias",
    "pizzerias y hamburgueserias",
    "boutiques y tiendas de regalos",
    "salones de eventos y banquetes"
]

# Giros y palabras clave estrictamente excluidos por orden de Sebastian
EXCLUDED_KEYWORDS = [
    "taller", "mecanic", "mecánic", "automotriz", "refaccion", "refacción",
    "llanta", "freno", "afinacion", "afinación", "hojalater", "suspension", "autolavado",
    "dental", "dentist", "odontol", "clinica dental", "clínica dental", "dientes", "ortodon"
]

def _is_excluded_business(name: str, niche: str, text: str = "") -> bool:
    """Verifica si un negocio pertenece a giros excluidos (talleres mecanicos o clinicas dentales)."""
    target = f"{name} {niche} {text}".lower()
    return any(w in target for w in EXCLUDED_KEYWORDS)

# Ciudades de la Comarca Lagunera por defecto
LAGUNA_CITIES = ["Torreón", "Gómez Palacio", "Ciudad Lerdo"]

def _resolve_target_cities(city_input: str) -> list:
    """Resuelve la lista de ciudades a prospectar, priorizando la Comarca Lagunera (Torreón, Gómez Palacio y Lerdo)."""
    c = (city_input or "").lower().strip()
    if not c or any(w in c for w in ["laguna", "comarca", "triada", "tríada", "metro", "todos", "general"]):
        return LAGUNA_CITIES

    matched = []
    if "torreon" in c or "torreón" in c:
        matched.append("Torreón")
    if "gomez" in c or "gómez" in c:
        matched.append("Gómez Palacio")
    if "lerdo" in c:
        matched.append("Ciudad Lerdo")

    if matched:
        return matched

    return [city_input.strip()]

def _load_leads() -> list:
    if not LEADS_FILE.exists():
        return []
    try:
        with open(LEADS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _save_leads(leads: list):
    with open(LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump(leads, f, indent=2, ensure_ascii=False)

def _clean_business_name(title: str, href: str, niche: str) -> str:
    """Limpia y da formato profesional al nombre del negocio extraído."""
    name = re.sub(r"\s*[-|–|—|•|/|\|].*$", "", title).strip()
    name = re.sub(r"(?i)\b(directorio|telefonos?|contactos?|whatsapp|facebook|fb|mexico|coahuila|durango|laguna|comarca lagunera|torreon|gomez palacio|gomez|lerdo|cd lerdo|nuevo leon|portal|pagina|oficial|horario|opiniones)\b", "", name).strip()
    if len(name) < 4 or name.lower() in ["inicio", "home", "contacto", "principal", "bienvenido", "sucursal", "telefono", "teléfono", "telefonos", "directorio", "whatsapp"]:
        match = re.search(r"https?://(?:www\.)?([^/.]+)", href)
        if match and match.group(1) not in ["google", "facebook", "instagram", "doctoralia", "seccionamarilla", "guiatel"]:
            domain_name = match.group(1).replace("-", " ").replace("_", " ").title()
            return domain_name
        return f"Negocio de {niche.title()}"
    return name.title()

def normalize_mx_phone(raw: str) -> str:
    """Normaliza un numero de telefono mexicano al formato internacional de WhatsApp."""
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return ""
    if digits.startswith("521") and len(digits) == 13:
        return digits
    if digits.startswith("52") and len(digits) == 12:
        return "521" + digits[2:]
    if len(digits) == 10:
        return "521" + digits
    if (digits.startswith("044") or digits.startswith("045")) and len(digits) >= 13:
        return "521" + digits[3:13]
    return digits

def discover_leads(niche: str = "", city: str = "Torreón, Gómez Palacio y Lerdo", max_leads: int = 5) -> list:
    """Explora la web, directorios y mapas locales para identificar prospectos de CUALQUIER tipo de negocio con teléfono en Torreón, Gómez Palacio y Lerdo.
    
    Args:
        niche: Giro o categoría (ej. 'talleres mecánicos', 'restaurantes', 'arquitectura', 'abogados', 'gimnasios', 'mueblerías', etc.). Si está vacío o es 'cualquiera', busca en giros variados.
        city: Ciudad o región a prospectar (por defecto busca en la Comarca Lagunera: Torreón, Gómez Palacio y Lerdo).
        max_leads: Número de prospectos a identificar.
    """
    existing_leads = _load_leads()
    seen_phones = {l.get("phone") for l in existing_leads if l.get("phone")}
    discovered = []

    target_niches = []
    clean_niche_input = (niche or "").lower().strip()

    if not clean_niche_input or any(w in clean_niche_input for w in ["cualquier", "todos", "general", "negocios", "empresas", "locales", "pymes", "variados"]):
        target_niches = DIVERSE_NICHES
    else:
        target_niches = [clean_niche_input]

    target_cities = _resolve_target_cities(city)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    try:
        with DDGS() as ddgs:
            for current_city in target_cities:
                if len(discovered) >= max_leads:
                    break

                for current_niche in target_niches:
                    if len(discovered) >= max_leads:
                        break

                    queries = [
                        f"{current_niche} {current_city} whatsapp pedidos",
                        f"facebook {current_niche} {current_city} whatsapp",
                        f"{current_niche} en {current_city} telefono",
                        f"facebook {current_niche} {current_city} telefono 871"
                    ]

                    for q in queries:
                        if len(discovered) >= max_leads:
                            break
                        try:
                            results = list(ddgs.text(q, max_results=6))
                        except Exception:
                            continue

                        for r in results:
                            if len(discovered) >= max_leads:
                                break

                            title = r.get("title", "")
                            body = r.get("body", "")
                            href = r.get("href", "")

                            # 1. Extracción directa de teléfonos en el snippet
                            raw_phones = re.findall(r"(?:(?:\+?52\s?)?(?:\(?\d{2,3}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4})", body)
                            for rp in raw_phones:
                                norm = normalize_mx_phone(rp)
                                if len(norm) == 13 and norm not in seen_phones:
                                    b_name = _clean_business_name(title, href, current_niche)
                                    if _is_excluded_business(b_name, current_niche, body):
                                        continue
                                    seen_phones.add(norm)
                                    discovered.append({
                                        "name": b_name,
                                        "phone": norm,
                                        "city": current_city,
                                        "niche": current_niche,
                                        "source": href,
                                        "notes": f"Negocio de {current_niche} en {current_city} detectado en directorio web.",
                                        "status": "nuevo",
                                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    })
                                    if len(discovered) >= max_leads:
                                        break

                            # 2. Si el enlace es de directorios con fichas
                            if len(discovered) < max_leads and any(d in href for d in ["guiatel", "cercademiubicacion", "seccionamarilla", "buscodentista", "arquimex", "pymes.org"]):
                                try:
                                    with httpx.Client(timeout=6.0, follow_redirects=True, verify=False) as client:
                                        resp = client.get(href, headers=headers)
                                    if resp.status_code == 200:
                                        soup = BeautifulSoup(resp.text, "html.parser")
                                        for elem in soup.find_all(["h2", "h3", "strong"]):
                                            if len(discovered) >= max_leads:
                                                break
                                            parent = elem.find_parent(["div", "li", "article", "tr"])
                                            parent_text = parent.get_text(separator=" ", strip=True) if parent else ""
                                            page_phones = re.findall(r"(?:(?:\+?52\s?)?(?:\(?\d{2,3}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4})", parent_text)
                                            for ph in page_phones:
                                                norm_ph = normalize_mx_phone(ph)
                                                if len(norm_ph) == 13 and norm_ph not in seen_phones:
                                                    h_raw = elem.get_text().strip()
                                                    if len(h_raw) > 3 and not any(ign in h_raw.lower() for ign in ["telefono", "directorio", "buscar", "contacto", "horario"]):
                                                        h_name = _clean_business_name(h_raw, href, current_niche)
                                                        if _is_excluded_business(h_name, current_niche, parent_text):
                                                            continue
                                                        seen_phones.add(norm_ph)
                                                        discovered.append({
                                                            "name": h_name,
                                                            "phone": norm_ph,
                                                            "city": current_city,
                                                            "niche": current_niche,
                                                            "source": href,
                                                            "notes": f"Ficha comercial de {current_niche} en {current_city} sin plataforma web moderna.",
                                                            "status": "nuevo",
                                                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                                        })
                                                        if len(discovered) >= max_leads:
                                                            break
                                except Exception:
                                    continue
    except Exception as e:
        logger.error("Error durante prospeccion web: %s", e)

    return discovered

def search_business_leads(niche: str = "", city: str = "Torreón, Gómez Palacio y Lerdo", max_results: int = 5) -> str:
    """Busca cualquier tipo de negocio local en Torreón, Gómez Palacio y Lerdo para encontrar prospectos de desarrollo y diseño web.
    
    Args:
        niche: Opcional, tipo de negocio (ej. 'talleres mecánicos', 'restaurantes', 'arquitectura', 'abogados', 'gimnasios', 'mueblerías', etc.). Si se omite o es 'cualquiera', busca en variedad de giros.
        city: Ciudad o región (por defecto 'Torreón, Gómez Palacio y Lerdo').
        max_results: Cantidad de prospectos a identificar.
    """
    niche_label = niche if niche else "cualquier tipo de negocio"
    leads = discover_leads(niche=niche, city=city, max_leads=max_results)
    if not leads:
        return f"No se encontraron nuevos prospectos con teléfono disponible para [{niche_label}] en [{city}] en este intento."

    lines = [f"Prospectos de negocios identificados en [{city}] ({niche_label}):"]
    for i, l in enumerate(leads, 1):
        lines.append(f"{i}. {l['name']} | Tel WhatsApp: {l['phone']} | Ciudad: {l.get('city', 'La Laguna')} | Giro: {l.get('niche', 'comercial')} | Fuente: {l.get('source', '')[:60]}")
    lines.append("\nPuedes guardar estos prospectos con save_lead o ejecutar run_autonomous_campaign para contactarlos automáticamente por WhatsApp.")
    return "\n".join(lines)

def generate_pitch(business_name: str, niche: str = "", contact_name: str = "") -> str:
    """Genera una propuesta personalizada y elegante adaptada específicamente al giro de CUALQUIER negocio, mostrando exclusivamente el portafolio y el Instagram oficial de SSSSolutions.
    
    Args:
        business_name: Nombre del negocio prospecto.
        niche: Giro o actividad del negocio (ej. 'restaurante', 'taller mecánico', 'arquitectura', 'gimnasio', 'abogados', 'mueblería', 'clínica').
        contact_name: Opcional, nombre de la persona o encargado si se conoce.
    """
    greeting = f"Hola {contact_name}," if contact_name else f"Hola equipo de {business_name},"
    niche_lower = (niche or "").lower()

    # Personalización del beneficio según la industria del negocio
    if any(k in niche_lower for k in ["cafe", "cafeter", "coffee"]):
        benefit = "atraer nuevos clientes, exhibir sus bebidas y especialidades de forma visual y recibir pedidos para llevar o a domicilio directamente en su WhatsApp"
    elif any(k in niche_lower for k in ["dulce", "dulcer", "confiter", "botan", "snack"]):
        benefit = "mostrar su catálogo de dulces, botanas y paquetes para fiestas y recibir pedidos por mayoreo o menudeo directamente en su WhatsApp"
    elif any(k in niche_lower for k in ["flor", "florer", "arreglo", "ramo", "planta"]):
        benefit = "exhibir su catálogo de ramos y arreglos florales de temporada, facilitando que los clientes elijan y coordinen envíos a domicilio al instante"
    elif any(k in niche_lower for k in ["pastel", "reposter", "panader", "horno", "pan"]):
        benefit = "mostrar su galería de pasteles personalizados y repostería artesanal, permitiendo a los clientes cotizar y encargar sus pedidos para eventos fácilmente"
    elif any(k in niche_lower for k in ["nieve", "helad", "palet", "postre"]):
        benefit = "exhibir sus sabores de temporada, promociones y especialidades de forma visual y atractiva para atraer clientes locales"
    elif any(k in niche_lower for k in ["restauran", "comida", "bar", "pizza", "taco", "hamburgues", "gastronom", "cocina"]):
        benefit = "atraer nuevos comensales, exhibir su menú interactivo de forma visual y recibir reservaciones o pedidos directamente en su WhatsApp"
    elif any(k in niche_lower for k in ["boutique", "regalo", "tienda", "ropa", "joyer", "accesorio"]):
        benefit = "contar con un catálogo visual digital donde los clientes puedan explorar sus colecciones y consultar disponibilidad y precios al instante"
    elif any(k in niche_lower for k in ["salon", "evento", "banquet", "fiesta"]):
        benefit = "exhibir sus paquetes para eventos, galerías de montajes y recibir solicitudes de cotización y fechas disponibles directamente en su WhatsApp"
    else:
        benefit = "contar con una plataforma web profesional, ultra rápida y optimizada para dispositivos móviles que posicione su marca e impulse sus ventas y pedidos por WhatsApp"

    portfolio_url = PORTFOLIO_LINKS["portfolio"]
    ig_url = PORTFOLIO_LINKS["instagram"]

    pitch = (
        f"{greeting}\n\n"
        f"Les escribe Sebastián Salinas, fundador de la agencia de desarrollo web y software SSSSolutions (@ssss.olutions).\n\n"
        f"Estuvimos revisando la presencia digital de los negocios del sector en su zona y notamos una excelente "
        f"oportunidad para que {business_name} cuente con una plataforma web propia de alto impacto que les permita {benefit}.\n\n"
        f"En SSSSolutions nos especializamos en diseño web moderno, desarrollo de software a medida y páginas de alta conversión:\n"
        f"• Portafolio: {portfolio_url}\n"
        f"• Instagram: {ig_url}\n\n"
        f"¿Les gustaría agendar una breve llamada para comentar cómo podemos impulsar la presencia digital de {business_name}?"
    )
    return pitch

def save_lead(name: str, phone: str, niche: str = "general", notes: str = "") -> str:
    """Guarda un negocio prospectado en el registro de clientes potenciales.
    
    Args:
        name: Nombre del negocio o empresa.
        phone: Teléfono o WhatsApp de contacto.
        niche: Giro o categoría (ej. 'taller mecánico', 'restaurante', 'mueblería', 'arquitectura', etc.).
        notes: Observaciones (ej. 'No tiene sitio web actual', 'Solo maneja Facebook').
    """
    leads = _load_leads()
    norm_phone = normalize_mx_phone(phone)
    lead_id = len(leads) + 1
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for existing in leads:
        if existing.get("phone") == norm_phone:
            return f"El prospecto con teléfono {norm_phone} ya se encontraba registrado bajo el nombre '{existing.get('name')}'."

    new_lead = {
        "id": lead_id,
        "name": name,
        "phone": norm_phone,
        "niche": niche,
        "notes": notes,
        "status": "nuevo",
        "created_at": now
    }
    leads.append(new_lead)
    _save_leads(leads)
    return f"Prospecto guardado exitosamente: [{name}] | Tel WhatsApp: {norm_phone} | ID: {lead_id}"

def list_leads(status_filter: str = "") -> str:
    """Lista todos los prospectos y negocios registrados en el sistema.
    
    Args:
        status_filter: Opcional, filtrar por estado ('nuevo', 'contactado', 'respondio', 'interesado').
    """
    leads = _load_leads()
    if not leads:
        return "No hay prospectos registrados actualmente."

    filtered = leads
    if status_filter:
        filtered = [l for l in leads if l.get("status", "").lower() == status_filter.lower()]

    if not filtered:
        return f"No se encontraron prospectos con estado '{status_filter}'."

    lines = [f"PROSPECTOS REGISTRADOS ({len(filtered)}):"]
    for l in filtered:
        lines.append(f"• ID {l['id']}: {l['name']} | Tel: {l['phone']} | Giro: {l.get('niche', 'general')} | Estado: [{l.get('status', 'nuevo').upper()}]")
        if l.get("notes"):
            lines.append(f"  Detalles: {l['notes']}")
        if l.get("contacted_at"):
            lines.append(f"  Fecha de contacto: {l['contacted_at']}")
    return "\n".join(lines)

def update_lead_status(lead_id: int, status: str, notes: str = "") -> str:
    """Actualiza el estado de un prospecto (ej. 'contactado', 'respondio', 'interesado', 'descartado')."""
    leads = _load_leads()
    for l in leads:
        if l.get("id") == lead_id:
            l["status"] = status.lower()
            if notes:
                l["notes"] = (l.get("notes", "") + f" | {notes}").strip(" | ")
            _save_leads(leads)
            return f"Prospecto ID {lead_id} [{l['name']}] actualizado a estado '{status}'."
    return f"No se encontró ningún prospecto con ID {lead_id}."

def run_autonomous_campaign(niche: str = "", city: str = "Torreón, Gómez Palacio y Lerdo", count: int = 3, auto_send: bool = True) -> str:
    """Ejecuta una campaña autónoma de prospección para CUALQUIER tipo de negocio en Torreón, Gómez Palacio y Lerdo: busca negocios locales con teléfono, genera el concepto web interactivo exclusivo, la propuesta personalizada con el Instagram y portafolio de SSSSolutions, y les envía el mensaje por WhatsApp de forma segura.
    
    Args:
        niche: Giro o categoría (ej. 'talleres mecánicos', 'restaurantes', 'mueblerías', 'arquitectura', 'abogados', 'gimnasios', etc.). Si está vacío o es 'cualquiera', busca en variedad de giros.
        city: Ciudades a prospectar (por defecto 'Torreón, Gómez Palacio y Lerdo').
        count: Número de prospectos a contactar en esta campaña (recomendado entre 1 y 5).
        auto_send: Si es True, envía el mensaje por WhatsApp inmediatamente con espaciado de seguridad. Si es False, solo genera y guarda los prospectos y propuestas.
    """
    niche_label = niche if niche else "cualquier tipo de negocio"
    leads_found = discover_leads(niche=niche, city=city, max_leads=count)
    if not leads_found:
        return f"No se pudieron encontrar prospectos nuevos con teléfono válido para [{niche_label}] en [{city}]."

    existing_leads = _load_leads()
    results_summary = []
    contacted_count = 0

    for item in leads_found:
        lead_id = len(existing_leads) + 1
        item_niche = item.get("niche", niche or "general")
        pitch = generate_pitch(business_name=item["name"], niche=item_niche)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lead_record = {
            "id": lead_id,
            "name": item["name"],
            "phone": item["phone"],
            "city": item.get("city", city),
            "niche": item_niche,
            "source": item.get("source", ""),
            "notes": item.get("notes", ""),
            "created_at": now_str,
            "pitch": pitch,
            "status": "nuevo"
        }

        if auto_send:
            send_result = send_whatsapp_message(to_number=item["phone"], message=pitch)
            if is_delivery_confirmed(send_result):
                lead_record["status"] = "contactado"
                lead_record["contacted_at"] = now_str
                contacted_count += 1
                results_summary.append(f"• ID {lead_id}: {item['name']} ({item['phone']}) [{item_niche}] -> Contactado por WhatsApp")
            elif is_delivery_pending(send_result):
                lead_record["status"] = "pendiente_confirmacion"
                lead_record["notes"] += f" | Entrega pendiente de confirmación: {send_result}"
                results_summary.append(f"• ID {lead_id}: {item['name']} ({item['phone']}) [{item_niche}] -> Pendiente de confirmación")
            else:
                lead_record["status"] = "error_envio"
                lead_record["notes"] += f" | Error envio: {send_result}"
                results_summary.append(f"• ID {lead_id}: {item['name']} ({item['phone']}) [{item_niche}] -> Fallo envio: {send_result}")

            # Pausa de seguridad de 8 segundos entre envíos para proteger el número
            if len(leads_found) > 1:
                time.sleep(8)
        else:
            results_summary.append(f"• ID {lead_id}: {item['name']} ({item['phone']}) [{item_niche}] -> Guardado en espera de aprobacion")

        existing_leads.append(lead_record)

    _save_leads(existing_leads)

    summary_report = (
        f"REPORTE DE CAMPAÑA AUTÓNOMA SSSSOLUTIONS\n\n"
        f"Ciudad: {city} | Modo: Automático\n"
        f"Giro: {niche_label.title()}\n"
        f"Prospectos contactados con éxito: {contacted_count} de {len(leads_found)}\n\n"
        f"Detalle de negocios contactados:\n"
        + "\n".join(results_summary) + "\n\n"
        f"Enlaces enviados en cada propuesta:\n"
        f"• Portafolio: https://st24030217-maker.github.io/cv-salinas/\n"
        f"• Instagram: https://www.instagram.com/ssss.olutions\n\n"
        f"Monitoreo activo:\n"
        f"Sebax está monitoreando activamente este canal. Si cualquiera de estos negocios responde, Sebax les responderá automáticamente para resolver sus dudas y te enviará un aviso inmediato aquí mismo."
    )

    # Notificar también al WhatsApp personal de Sebastián para que esté enterado en tiempo real en su teléfono
    try:
        send_whatsapp_message(to_number="self", message=summary_report)
    except Exception as e:
        logger.warning("No se pudo enviar notificación de resumen a Sebastián: %s", e)

    return summary_report

async def generate_lead_reply(lead_name: str, lead_niche: str, incoming_message: str) -> str:
    """Genera una respuesta inteligente de Sebax para atender a un prospecto comercial que ha respondido en WhatsApp."""
    try:
        import asyncio
        from google import genai
        from agente.config import settings

        prompt = f"""Eres Sebax, el asistente comercial de la agencia SSSSolutions (@ssss.olutions), fundada por Sebastián Salinas.
Un cliente potencial de un negocio ({lead_name}, giro: {lead_niche}) ha respondido al mensaje de prospección con lo siguiente:
"{incoming_message}"

TU TAREA:
Responder con total amabilidad, profesionalismo y enfoque comercial para concertar una propuesta o llamada con Sebastián Salinas.

REGLAS ESTRICTAS:
- NUNCA uses emojis en ninguna circunstancia.
- Responde a su consulta de forma directa:
  * Si pregunta sobre precios, aclara que manejamos paquetes muy accesibles para negocios locales y cotizaciones a la medida sin ningún costo.
  * Si pregunta qué incluye, explica que incluye diseño responsivo para móviles, velocidad ultra rápida, dominio, hosting y botón directo a su WhatsApp.
  * Si propone o solicita agendar una cita, llamada o reunión, confirma con entusiasmo y propón dos horarios claros (ejemplo: 'Con gusto coordinamos una breve llamada con Sebastián Salinas mañana a las 11:00 AM o a las 4:00 PM, ¿cuál le resulta más conveniente?').
- Menciona que pueden revisar el portafolio oficial: https://st24030217-maker.github.io/cv-salinas/ y el Instagram: https://www.instagram.com/ssss.olutions.
- NUNCA incluyas repositorios de GitHub ni proyectos personales. SOLO el portafolio y el Instagram.
- Invita cordialmente a agendar una breve llamada o prepararles una propuesta visual inicial con Sebastián Salinas.
- Mantén la respuesta breve (1 o 2 párrafos concisos).
"""
        client = genai.Client(api_key=settings.gemini_api_key)
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.gemini_model,
            contents=prompt
        )
        if response.text:
            return response.text.strip()
    except Exception as e:
        logger.error("Error al generar respuesta automática para lead: %s", e)

    return (
        f"Hola. Un gusto saludarle. Le atiende Sebax, asistente comercial de SSSSolutions, agencia fundada por Sebastián Salinas. "
        f"Con gusto podemos prepararles una cotización y propuesta visual sin costo para {lead_name}. "
        f"Nuestros desarrollos incluyen diseño responsivo para celulares, velocidad de carga y botón directo a su WhatsApp. "
        f"Pueden consultar nuestro portafolio en https://st24030217-maker.github.io/cv-salinas/ y en Instagram https://www.instagram.com/ssss.olutions. "
        f"¿Le parecería bien agendar una breve llamada con Sebastián Salinas para platicar de los detalles?"
    )

def get_leads_stats() -> dict:
    """Devuelve estadísticas y lista de prospectos para el panel web y API."""
    leads = _load_leads()
    total = len(leads)
    contactados = sum(1 for l in leads if l.get("status") == "contactado")
    respondieron = sum(1 for l in leads if l.get("status") == "respondio")
    nuevos = sum(1 for l in leads if l.get("status") == "nuevo")

    return {
        "total": total,
        "contactados": contactados,
        "respondieron": respondieron,
        "nuevos": nuevos,
        "leads": sorted(leads, key=lambda x: x.get("id", 0), reverse=True)
    }
