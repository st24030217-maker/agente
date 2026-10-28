import re
import os
import logging
from pathlib import Path
from agente.config import DATA_DIR

logger = logging.getLogger(__name__)

PREVIEWS_DIR = DATA_DIR / "previews"
PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)

PORTFOLIO_URL = "https://st24030217-maker.github.io/cv-salinas/"
INSTAGRAM_URL = "https://www.instagram.com/ssss.olutions"

def get_base_url() -> str:
    """Obtiene la URL pública base del servicio (Render o local)."""
    env_url = os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("PUBLIC_BASE_URL")
    if env_url:
        return env_url.rstrip("/")
    # URL oficial desplegada en Render por defecto
    return "https://agente-hgba.onrender.com"

def slugify(text: str) -> str:
    """Convierte un nombre en un slug seguro para URLs."""
    text = text.lower()
    text = re.sub(r'[áàäâ]', 'a', text)
    text = re.sub(r'[éèëê]', 'e', text)
    text = re.sub(r'[íìïî]', 'i', text)
    text = re.sub(r'[óòöô]', 'o', text)
    text = re.sub(r'[úùüû]', 'u', text)
    text = re.sub(r'ñ', 'n', text)
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-') or "demo"

def _get_industry_theme(niche: str) -> dict:
    n = (niche or "").lower()

    if any(k in n for k in ["restauran", "comida", "cafe", "bar", "pizza", "taco", "gastronom", "cocina"]):
        return {
            "category": "Restaurante & Gastronomía",
            "tagline": "Experiencia Gastronómica de Primer Nivel",
            "hero_desc": "Descubre una propuesta única de sabor, ingredientes frescos y un ambiente preparado para recibirte.",
            "services": [
                {"title": "Menú Digital Interactivo", "desc": "Platillos con fotos de alta resolución y precios actualizados al instante."},
                {"title": "Reservaciones en Línea", "desc": "Aparta tu mesa en segundos directamente desde tu teléfono celular."},
                {"title": "Pedidos a Domicilio", "desc": "Envío de pedidos rápidos y claros sin comisiones excesivas."}
            ],
            "accent": "#e11d48",
            "accent_light": "#ffe4e6",
            "cta": "Hacer Reservación / Pedido",
            "bg_hero": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=1200&q=80"
        }
    elif any(k in n for k in ["taller", "mecanic", "auto", "refaccion", "llant", "freno", "electrico", "motor"]):
        return {
            "category": "Taller Mecánico & Mantenimiento Automotriz",
            "tagline": "Diagnóstico de Precisión y Servicio Mecánico Confiable",
            "hero_desc": "Cuidamos tu patrimonio con equipo de vanguardia, técnicos especializados y refacciones de la más alta calidad.",
            "services": [
                {"title": "Diagnóstico por Computadora", "desc": "Escaneo profesional de fallas de motor, sensores y sistemas electrónicos."},
                {"title": "Afinación & Frenos", "desc": "Mantenimiento preventivo y correctivo con garantía por escrito."},
                {"title": "Cotizaciones Transparentes", "desc": "Presupuestos claros antes de comenzar cualquier trabajo sin sorpresas."}
            ],
            "accent": "#0284c7",
            "accent_light": "#e0f2fe",
            "cta": "Cotizar Mantenimiento",
            "bg_hero": "https://images.unsplash.com/photo-1486006920555-c77dce18193b?auto=format&fit=crop&w=1200&q=80"
        }
    elif any(k in n for k in ["arqui", "inmob", "construc", "diseño interior", "bienes raic", "propied"]):
        return {
            "category": "Arquitectura & Desarrollo Inmobiliario",
            "tagline": "Espacios de Vanguardia Diseñados para Trascender",
            "hero_desc": "Diseñamos y construimos proyectos residenciales y comerciales donde la estética, la luz y la función conviven en armonía.",
            "services": [
                {"title": "Diseño Arquitectónico", "desc": "Planos ejecutivos, renders 3D hiperrealistas y modelado integral."},
                {"title": "Construcción & Obra", "desc": "Gestión rigurosa de tiempos, costos y calidad en cada etapa constructiva."},
                {"title": "Remodelación de Espacios", "desc": "Transformación integral de interiores para residencias y oficinas de lujo."}
            ],
            "accent": "#0f172a",
            "accent_light": "#f1f5f9",
            "cta": "Agendar Consulta de Proyecto",
            "bg_hero": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80"
        }
    elif any(k in n for k in ["dent", "salud", "medic", "clinic", "dental", "odontolog", "veterinar", "optica", "spa"]):
        return {
            "category": "Clínica & Especialistas de Salud",
            "tagline": "Atención Médica Integral para tu Bienestar",
            "hero_desc": "Instalaciones de primer nivel, tecnología médica avanzada y un equipo humano enfocado en tu salud y tranquilidad.",
            "services": [
                {"title": "Consultas Especializadas", "desc": "Evaluación personalizada con diagnósticos certeros y modernos."},
                {"title": "Tratamientos de Vanguardia", "desc": "Técnicas mínimamente invasivas con rápida recuperación."},
                {"title": "Citas Rápidas por WhatsApp", "desc": "Agenda tu consulta médica de manera fácil y sin filas de espera."}
            ],
            "accent": "#0d9488",
            "accent_light": "#ccfbf1",
            "cta": "Agendar Cita Médica",
            "bg_hero": "https://images.unsplash.com/photo-1629909613654-28e377c37b09?auto=format&fit=crop&w=1200&q=80"
        }
    elif any(k in n for k in ["gym", "gimnasio", "fit", "crossfit", "deport", "entrenam"]):
        return {
            "category": "Centro Deportivo & Entrenamiento",
            "tagline": "Alcanza tu Máximo Potencial Físico",
            "hero_desc": "Equipamiento de última generación, entrenadores certificados y la mejor comunidad para superar tus metas.",
            "services": [
                {"title": "Área de Fuerza y Cardio", "desc": "Maquinaria profesional de marcas líderes disponible todo el día."},
                {"title": "Clases Grupales", "desc": "Spinning, Cross Training, Funcional, Yoga y Pilates con instructores top."},
                {"title": "Planes Personalizados", "desc": "Seguimiento nutricional y rutinas adaptadas a tus objetivos."}
            ],
            "accent": "#f97316",
            "accent_light": "#ffedd5",
            "cta": "Obtener Pase de Prueba",
            "bg_hero": "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=1200&q=80"
        }
    elif any(k in n for k in ["abogad", "legal", "juridic", "contador", "fiscal", "notar", "consultor"]):
        return {
            "category": "Firma Legal & Asesoría Fiscal",
            "tagline": "Estrategia Legal y Protección Integral de tu Negocio",
            "hero_desc": "Soluciones jurídicas y contables sólidas para proteger tus inversiones, defender tus derechos y hacer crecer tu empresa.",
            "services": [
                {"title": "Defensa y Litigio Estratégico", "desc": "Representación rigurosa en materia mercantil, civil, fiscal y laboral."},
                {"title": "Consultoría Corporativa", "desc": "Constitución de sociedades, contratos y blindaje patrimonial para empresas."},
                {"title": "Planificación Fiscal", "desc": "Optimización contable y cumplimiento tributario conforme a la ley."}
            ],
            "accent": "#1e3a8a",
            "accent_light": "#dbeafe",
            "cta": "Solicitar Asesoría Privada",
            "bg_hero": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&q=80"
        }
    elif any(k in n for k in ["muebl", "tienda", "boutique", "ferreter", "comercio", "zapater", "ropa", "decoracion"]):
        return {
            "category": "Mueblería & Tienda de Diseño",
            "tagline": "Mobiliario y Diseños que Dan Vida a tus Espacios",
            "hero_desc": "Catálogo exclusivo de piezas fabricadas con acabados de primera y materiales de alta durabilidad para tu hogar u oficina.",
            "services": [
                {"title": "Catálogo de Temporada", "desc": "Colecciones exclusivas con entrega rápida y garantía de fábrica."},
                {"title": "Diseños a la Medida", "desc": "Fabricamos muebles personalizados adaptados a las dimensiones de tu espacio."},
                {"title": "Envíos e Instalación", "desc": "Transporte seguro y montaje profesional directamente en tu domicilio."}
            ],
            "accent": "#b45309",
            "accent_light": "#fef3c7",
            "cta": "Ver Catálogo y Cotizar",
            "bg_hero": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?auto=format&fit=crop&w=1200&q=80"
        }
    else:
        return {
            "category": "Empresa Comercial & Servicios Profesionales",
            "tagline": "Calidad, Confianza y Soluciones para tu Día a Día",
            "hero_desc": "Brindamos una experiencia de atención incomparable con estándares estrictos de calidad y compromiso total con cada cliente.",
            "services": [
                {"title": "Atención Personalizada", "desc": "Respuesta inmediata para cotizaciones y requerimientos específicos."},
                {"title": "Garantía de Satisfacción", "desc": "Procesos claros y respaldo total en cada uno de nuestros servicios."},
                {"title": "Facilidad de Contacto", "desc": "Comunicación ágil y directa por WhatsApp sin intermediarios."}
            ],
            "accent": "#2563eb",
            "accent_light": "#eff6ff",
            "cta": "Solicitar Información",
            "bg_hero": "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1200&q=80"
        }

def generate_business_mockup(business_name: str, niche: str = "", city: str = "Torreón", phone: str = "") -> dict:
    """Genera un prototipo visual interactivo de página web para un negocio prospectado.
    
    Args:
        business_name: Nombre comercial del negocio.
        niche: Giro o categoría (ej. 'taller mecánico', 'restaurante', 'mueblería', etc.).
        city: Ciudad donde se ubica el negocio.
        phone: Teléfono o WhatsApp de contacto.
        
    Returns:
        dict con slug, path del archivo generado y URL pública en vivo.
    """
    slug = slugify(business_name)
    theme = _get_industry_theme(niche)
    theme_category = theme["category"]
    theme_tagline = theme["tagline"]
    theme_hero_desc = theme["hero_desc"]
    theme_accent = theme["accent"]
    theme_cta = theme["cta"]
    theme_services = theme["services"]
    theme_hero_bg = theme["bg_hero"]

    clean_phone = re.sub(r"\D", "", phone or "")
    if clean_phone.startswith("521"):
        wa_target = clean_phone
    elif len(clean_phone) == 10:
        wa_target = "521" + clean_phone
    else:
        wa_target = clean_phone or "5218710000000"

    wa_link = f"https://wa.me/{wa_target}?text=Hola%20{slug.replace('-', '%20')},%20me%20gustar%C3%ADa%20solicitar%20informaci%C3%B3n"

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{business_name} | Sitio Oficial</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
    .accent-bg {{ background-color: {theme_accent}; }}
    .accent-text {{ color: {theme_accent}; }}
    .accent-border {{ border-color: {theme_accent}; }}
  </style>
</head>
<body class="bg-slate-50 text-slate-900 antialiased selection:bg-slate-900 selection:text-white">

  <!-- Banner Superior -->
  <div class="bg-slate-900 text-slate-300 text-xs py-2 px-4 text-center tracking-wide flex items-center justify-center gap-2">
    <span>Ubicación: <strong>{city}, México</strong></span>
    <span>•</span>
    <span>Atención inmediata vía WhatsApp</span>
  </div>

  <!-- Header / Barra de Navegación -->
  <header class="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-slate-200">
    <div class="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl accent-bg flex items-center justify-center text-white font-black text-lg shadow-sm">
          {business_name[:2].upper()}
        </div>
        <div>
          <h1 class="font-bold text-lg text-slate-900 leading-tight">{business_name}</h1>
          <p class="text-xs text-slate-500 font-medium">{theme_category}</p>
        </div>
      </div>
      <nav class="hidden md:flex items-center gap-6 text-sm font-medium text-slate-600">
        <a href="#servicios" class="hover:text-slate-900 transition">Servicios</a>
        <a href="#nosotros" class="hover:text-slate-900 transition">Por qué Elegirnos</a>
        <a href="#contacto" class="hover:text-slate-900 transition">Contacto</a>
      </nav>
      <div>
        <a href="{wa_link}" target="_blank" class="inline-flex items-center gap-2 accent-bg hover:opacity-95 text-white text-xs md:text-sm font-semibold px-4 py-2.5 rounded-xl shadow-sm transition">
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12.031 6.172c-3.181 0-5.767 2.586-5.768 5.766-.001 1.298.38 2.27 1.019 3.287l-.582 2.128 2.182-.573c.978.58 1.911.928 3.145.929 3.178 0 5.767-2.587 5.768-5.766.001-3.187-2.575-5.77-5.764-5.771zm3.392 8.244c-.144.405-.837.774-1.17.824-.299.045-.677.063-1.092-.069-.252-.08-.575-.187-.988-.365-1.739-.751-2.874-2.502-2.961-2.617-.087-.116-.708-.94-.708-1.793s.448-1.273.607-1.446c.159-.173.346-.217.462-.217l.332.007c.106.005.249-.04.39.299.144.347.491 1.2.534 1.288.043.087.072.188.014.304-.058.116-.087.188-.173.289l-.26.304c-.087.087-.179.182-.077.357.101.174.452.746.97 1.208.666.593 1.229.777 1.403.864.173.087.275.072.376-.044.101-.116.433-.505.549-.679.116-.174.231-.145.39-.087s1.011.477 1.184.564.289.13.332.203c.044.072.044.419-.1 1.024z"/></svg>
          <span>{theme_cta}</span>
        </a>
      </div>
    </div>
  </header>

  <!-- Hero Section -->
  <section class="relative bg-slate-900 text-white overflow-hidden py-20 md:py-28">
    <div class="absolute inset-0 z-0 opacity-25 bg-cover bg-center" style="background-image: url('{theme_hero_bg}');"></div>
    <div class="absolute inset-0 z-0 bg-gradient-to-r from-slate-950 via-slate-900/90 to-transparent"></div>
    <div class="relative z-10 max-w-6xl mx-auto px-4">
      <div class="max-w-2xl">
        <div class="inline-block px-3 py-1 rounded-full bg-white/10 text-slate-200 text-xs font-semibold uppercase tracking-wider mb-4 border border-white/10">
          {theme_category} • {city}
        </div>
        <h2 class="text-3xl md:text-5xl font-extrabold text-white leading-tight mb-6">
          {theme_tagline}
        </h2>
        <p class="text-base md:text-lg text-slate-300 mb-8 leading-relaxed">
          {theme_hero_desc}
        </p>
        <div class="flex flex-col sm:flex-row gap-3">
          <a href="{wa_link}" target="_blank" class="inline-flex items-center justify-center gap-2 accent-bg hover:opacity-95 text-white font-bold px-6 py-3.5 rounded-xl shadow-lg transition">
            <span>{theme_cta}</span>
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
          </a>
          <a href="#servicios" class="inline-flex items-center justify-center gap-2 bg-white/10 hover:bg-white/20 text-white font-semibold px-6 py-3.5 rounded-xl border border-white/20 transition">
            <span>Conocer Servicios</span>
          </a>
        </div>
      </div>
    </div>
  </section>

  <!-- Sección de Servicios Principales -->
  <section id="servicios" class="py-16 md:py-24 max-w-6xl mx-auto px-4">
    <div class="text-center max-w-2xl mx-auto mb-16">
      <span class="text-xs font-bold uppercase tracking-wider accent-text">Nuestra Oferta</span>
      <h3 class="text-2xl md:text-3xl font-extrabold text-slate-900 mt-2">Servicios Diseñados para Ti</h3>
      <p class="text-slate-600 mt-3 text-sm md:text-base">Brindamos una atención rápida, profesional y con garantía en cada uno de nuestros procesos.</p>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div class="bg-white p-7 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition">
        <div class="w-12 h-12 rounded-xl accent-bg/10 flex items-center justify-center mb-5">
          <span class="text-xl font-black accent-text">01</span>
        </div>
        <h4 class="text-lg font-bold text-slate-900 mb-2">{theme_services[0]['title']}</h4>
        <p class="text-slate-600 text-sm leading-relaxed">{theme_services[0]['desc']}</p>
      </div>
      <div class="bg-white p-7 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition">
        <div class="w-12 h-12 rounded-xl accent-bg/10 flex items-center justify-center mb-5">
          <span class="text-xl font-black accent-text">02</span>
        </div>
        <h4 class="text-lg font-bold text-slate-900 mb-2">{theme_services[1]['title']}</h4>
        <p class="text-slate-600 text-sm leading-relaxed">{theme_services[1]['desc']}</p>
      </div>
      <div class="bg-white p-7 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition">
        <div class="w-12 h-12 rounded-xl accent-bg/10 flex items-center justify-center mb-5">
          <span class="text-xl font-black accent-text">03</span>
        </div>
        <h4 class="text-lg font-bold text-slate-900 mb-2">{theme_services[2]['title']}</h4>
        <p class="text-slate-600 text-sm leading-relaxed">{theme_services[2]['desc']}</p>
      </div>
    </div>
  </section>

  <!-- Banner de Llamada a la Acción -->
  <section class="bg-slate-900 text-white py-16 px-4">
    <div class="max-w-4xl mx-auto text-center">
      <h3 class="text-2xl md:text-4xl font-extrabold mb-4">¿Listo para contactar a {business_name}?</h3>
      <p class="text-slate-300 text-sm md:text-base max-w-xl mx-auto mb-8">
        Escríbenos directamente a nuestro WhatsApp oficial y recibe atención inmediata de nuestro equipo en {city}.
      </p>
      <a href="{wa_link}" target="_blank" class="inline-flex items-center gap-3 accent-bg hover:opacity-95 text-white font-bold px-8 py-4 rounded-xl text-base shadow-lg transition">
        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M12.031 6.172c-3.181 0-5.767 2.586-5.768 5.766-.001 1.298.38 2.27 1.019 3.287l-.582 2.128 2.182-.573c.978.58 1.911.928 3.145.929 3.178 0 5.767-2.587 5.768-5.766.001-3.187-2.575-5.77-5.764-5.771zm3.392 8.244c-.144.405-.837.774-1.17.824-.299.045-.677.063-1.092-.069-.252-.08-.575-.187-.988-.365-1.739-.751-2.874-2.502-2.961-2.617-.087-.116-.708-.94-.708-1.793s.448-1.273.607-1.446c.159-.173.346-.217.462-.217l.332.007c.106.005.249-.04.39.299.144.347.491 1.2.534 1.288.043.087.072.188.014.304-.058.116-.087.188-.173.289l-.26.304c-.087.087-.179.182-.077.357.101.174.452.746.97 1.208.666.593 1.229.777 1.403.864.173.087.275.072.376-.044.101-.116.433-.505.549-.679.116-.174.231-.145.39-.087s1.011.477 1.184.564.289.13.332.203c.044.072.044.419-.1 1.024z"/></svg>
        <span>Enviar Mensaje por WhatsApp</span>
      </a>
    </div>
  </section>

  <!-- Footer -->
  <footer class="bg-white border-t border-slate-200 py-8 px-4 text-center text-xs text-slate-500">
    <div class="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
      <div>
        <p class="font-bold text-slate-700">{business_name}</p>
        <p>{theme_category} • {city}, México</p>
      </div>
      <div>
        <p>Sitio web optimizado para dispositivos móviles y alta conversión.</p>
      </div>
    </div>
  </footer>

  <!-- SSSSolutions Agency Floating Badge -->
  <aside class="fixed bottom-3 right-3 left-3 md:left-auto md:max-w-md z-50 bg-slate-900/95 backdrop-blur-md text-white border border-slate-700 p-3.5 rounded-2xl shadow-2xl flex items-center justify-between gap-3 text-xs">
    <div class="flex items-center gap-2.5">
      <div class="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></div>
      <div>
        <p class="font-bold text-slate-100">Concepto Visual en Vivo</p>
        <p class="text-slate-400 text-[11px]">Diseñado por <strong>SSSSolutions</strong> (@ssss.olutions)</p>
      </div>
    </div>
    <a href="{PORTFOLIO_URL}" target="_blank" class="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white font-semibold text-[11px] border border-white/20 transition whitespace-nowrap">
      Ver Portafolio
    </a>
  </aside>

</body>
</html>
"""
    preview_file = PREVIEWS_DIR / f"{slug}.html"
    with open(preview_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    base_url = get_base_url()
    public_url = f"{base_url}/preview/{slug}"

    return {
        "slug": slug,
        "file_path": str(preview_file),
        "url": public_url,
        "business_name": business_name,
        "niche": niche,
        "city": city
    }
