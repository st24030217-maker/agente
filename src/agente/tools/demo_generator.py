import json
import re
import html
import urllib.parse
from pathlib import Path
from datetime import datetime
from agente.config import DATA_DIR

DEMOS_FILE = DATA_DIR / "demos.json"

NICHE_TEMPLATES = {
    "cafeteria": {
        "title": "Cafetería de Especialidad",
        "tagline": "Café de origen, repostería artesanal y momentos únicos en La Laguna.",
        "primary_color": "#f59e0b",
        "accent_color": "#d97706",
        "bg_color": "#0c0a09",
        "categories": ["Café Caliente", "Bebidas Frías", "Repostería", "Desayunos"],
        "items": [
            {
                "id": "c1",
                "name": "Americano de Especialidad",
                "cat": "Café Caliente",
                "price": 55,
                "desc": "Extracción doble de granos seleccionados de Chiapas y Oaxaca con notas a chocolate y avellana."
            },
            {
                "id": "c2",
                "name": "Flat White Artesanal",
                "cat": "Café Caliente",
                "price": 68,
                "desc": "Doble ristretto con microespuma de leche sedosa a temperatura perfecta."
            },
            {
                "id": "c3",
                "name": "Cold Brew Nitro Lagunero",
                "cat": "Bebidas Frías",
                "price": 75,
                "desc": "Maceración en frío por 18 horas infusionado con nitrógeno para una textura cremosa."
            },
            {
                "id": "c4",
                "name": "Iced Matcha Latte",
                "cat": "Bebidas Frías",
                "price": 80,
                "desc": "Matcha ceremonial japonés con leche de avena y un toque de vainilla natural."
            },
            {
                "id": "c5",
                "name": "Croissant Francés de Mantequilla",
                "cat": "Repostería",
                "price": 52,
                "desc": "Hojaldrado tradicional con mantequilla de alta calidad, dorado y crujiente."
            },
            {
                "id": "c6",
                "name": "Toast de Aguacate y Huevo Poché",
                "cat": "Desayunos",
                "price": 98,
                "desc": "Pan rústico de masa madre, aguacate fresco, semillas tostadas y aceite de oliva virgen."
            }
        ]
    },
    "restaurante": {
        "title": "Restaurante y Cocina Urbana",
        "tagline": "Sabor auténtico, ingredientes de primera y servicio directo a tu mesa o domicilio.",
        "primary_color": "#ef4444",
        "accent_color": "#dc2626",
        "bg_color": "#09090b",
        "categories": ["Especialidades", "Tacos y Costras", "Entradas", "Bebidas"],
        "items": [
            {
                "id": "r1",
                "name": "Orden de Tacos al Pastor Especial (5 piezas)",
                "cat": "Tacos y Costras",
                "price": 95,
                "desc": "Carne marinada con receta secreta, piña asada, cebolla y cilantro en tortilla hecha a mano."
            },
            {
                "id": "r2",
                "name": "Costra de Arrachera con Queso Menonita",
                "cat": "Tacos y Costras",
                "price": 115,
                "desc": "Arrachera marinada al carbón envuelta en costra crujiente de queso sobre tortilla de harina."
            },
            {
                "id": "r3",
                "name": "Gringa Suprema de Asada",
                "cat": "Especialidades",
                "price": 85,
                "desc": "Doble tortilla de harina con queso fundido y carne asada al punto."
            },
            {
                "id": "r4",
                "name": "Guacamole Tradicional con Totopos",
                "cat": "Entradas",
                "price": 80,
                "desc": "Aguacate fresco preparado al momento con pico de gallo y totopos de maíz azul."
            },
            {
                "id": "r5",
                "name": "Agua Fresca Natural de Temporada (1 Litro)",
                "cat": "Bebidas",
                "price": 45,
                "desc": "Horchata artesanal con canela o Jamaica fresca 100% natural."
            }
        ]
    },
    "pasteleria": {
        "title": "Pastelería y Repostería Fina",
        "tagline": "Diseños personalizados, texturas delicadas y el toque dulce que tus eventos merecen.",
        "primary_color": "#ec4899",
        "accent_color": "#db2777",
        "bg_color": "#0b0a0f",
        "categories": ["Pasteles de Línea", "Individuales", "Galletas", "Postres Especiales"],
        "items": [
            {
                "id": "p1",
                "name": "Pastel Tres Leches Frutos Rojos (12 personas)",
                "cat": "Pasteles de Línea",
                "price": 380,
                "desc": "Bizcocho esponjoso bañado en infusión de tres leches con fresas, zarzamoras y crema batida."
            },
            {
                "id": "p2",
                "name": "Cheesecake Horneado Estilo Nueva York",
                "cat": "Pasteles de Línea",
                "price": 360,
                "desc": "Cremoso con base de galleta de mantequilla y coulis artesanal de frutos silvestres."
            },
            {
                "id": "p3",
                "name": "Caja de Cupcakes Gourmet (6 piezas)",
                "cat": "Individuales",
                "price": 180,
                "desc": "Sabores surtidos: Red Velvet, Chocolate Belga, Zanahoria con Nuez y Vainilla Francesa."
            },
            {
                "id": "p4",
                "name": "Galletas Choco-Nut Rellenas (4 piezas)",
                "cat": "Galletas",
                "price": 125,
                "desc": "Galletas gigantes con chispas de chocolate belga y centro líquido de avellana."
            }
        ]
    },
    "floreria": {
        "title": "Florería y Diseños Botánicos",
        "tagline": "Flores frescas de invernadero y arreglos que transmiten emociones memorables.",
        "primary_color": "#10b981",
        "accent_color": "#059669",
        "bg_color": "#060908",
        "categories": ["Ramos Premium", "Cajas de Lujo", "Arreglos Florales", "Plantas"],
        "items": [
            {
                "id": "f1",
                "name": "Ramo Bouquet de 24 Rosas Rojas Premium",
                "cat": "Ramos Premium",
                "price": 680,
                "desc": "Rosas seleccionadas de tallo largo con follaje fino y envoltura de papel coreano mate."
            },
            {
                "id": "f2",
                "name": "Sombrerera Luxury con Rosas y Chocolates",
                "cat": "Cajas de Lujo",
                "price": 850,
                "desc": "Caja cilíndrica de diseño con rosas preservadas y selección de bombones artesanales."
            },
            {
                "id": "f3",
                "name": "Arreglo Silvestre de Lilis y Eucalipto",
                "cat": "Arreglos Florales",
                "price": 540,
                "desc": "Combinación fresca y aromática en florero de vidrio transparente con listón de seda."
            }
        ]
    },
    "boutique": {
        "title": "Boutique de Moda y Accesorios",
        "tagline": "Prendas seleccionadas, tendencias de temporada y estilo exclusivo en La Laguna.",
        "primary_color": "#38bdf8",
        "accent_color": "#0284c7",
        "bg_color": "#080c14",
        "categories": ["Prendas Clave", "Vestidos", "Accesorios", "Calzado"],
        "items": [
            {
                "id": "b1",
                "name": "Vestido Midi de Lino Silvestre",
                "cat": "Vestidos",
                "price": 720,
                "desc": "Tejido fresco 100% lino con ajuste en cintura y detalle de botones de concha nácar."
            },
            {
                "id": "b2",
                "name": "Conjunto Casual Urbano de Dos Piezas",
                "cat": "Prendas Clave",
                "price": 890,
                "desc": "Pantalón de corte amplio con top estructurado en tonos tierra neutros."
            },
            {
                "id": "b3",
                "name": "Bolso Tote de Estructura Minimalista",
                "cat": "Accesorios",
                "price": 540,
                "desc": "Cuero sintético de alto gramaje con herrajes en níquel satinado."
            }
        ]
    },
    "salon_eventos": {
        "title": "Salón y Jardín de Eventos",
        "tagline": "El escenario perfecto para tus celebraciones, banquetes y momentos inolvidables.",
        "primary_color": "#6366f1",
        "accent_color": "#4f46e5",
        "bg_color": "#080914",
        "categories": ["Paquetes de Evento", "Mobiliario", "Banquetes", "Extras"],
        "items": [
            {
                "id": "s1",
                "name": "Paquete Fiesta y Celebración (5 Horas)",
                "cat": "Paquetes de Evento",
                "price": 5200,
                "desc": "Renta de instalaciones climatizadas, sonido ambiental, personal de apoyo y limpieza incluida."
            },
            {
                "id": "s2",
                "name": "Mobiliario Vintage y Salas Lounge",
                "cat": "Mobiliario",
                "price": 1800,
                "desc": "Set de 2 salas lounge con mesas periqueras y sillas tipo Crossback de madera natural."
            },
            {
                "id": "s3",
                "name": "Barra de Bebidas y Coctelería sin Alcohol",
                "cat": "Extras",
                "price": 2400,
                "desc": "Servicio de barman con preparación de mocktails y refresquería para 80 invitados."
            }
        ]
    }
}

def _slugify(text: str) -> str:
    cleaned = text.lower().strip()
    cleaned = re.sub(r"[áàäâ]", "a", cleaned)
    cleaned = re.sub(r"[éèëê]", "e", cleaned)
    cleaned = re.sub(r"[íìïî]", "i", cleaned)
    cleaned = re.sub(r"[óòöô]", "o", cleaned)
    cleaned = re.sub(r"[úùüû]", "u", cleaned)
    cleaned = re.sub(r"[ñ]", "n", cleaned)
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned)
    return cleaned.strip("-")[:64]

def _detect_niche_key(niche: str) -> str:
    n = niche.lower()
    if any(k in n for k in ["cafe", "cafeteria", "coffee", "bistro"]):
        return "cafeteria"
    if any(k in n for k in ["restaurante", "taco", "comida", "asador", "pizz", "hamburg", "burger", "antojitos"]):
        return "restaurante"
    if any(k in n for k in ["pasteleria", "reposteria", "dulceria", "panaderia", "pastel", "cupcake", "postre"]):
        return "pasteleria"
    if any(k in n for k in ["flor", "floreria", "planta", "botanica", "jardin"]):
        return "floreria"
    if any(k in n for k in ["boutique", "ropa", "moda", "vestido", "calzado", "zapateria", "joyeria"]):
        return "boutique"
    if any(k in n for k in ["salon", "evento", "quince", "boda", "fiesta", "terraza"]):
        return "salon_eventos"
    return "cafeteria"

def _load_all_demos() -> dict:
    if DEMOS_FILE.exists():
        try:
            with open(DEMOS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_all_demos(demos: dict):
    with open(DEMOS_FILE, "w", encoding="utf-8") as f:
        json.dump(demos, f, ensure_ascii=False, indent=2)

def generate_business_demo(
    business_name: str,
    niche: str = "cafeteria",
    city: str = "Torreón, Coahuila",
    phone: str = "",
    custom_tagline: str = ""
) -> dict:
    """Genera un prototipo de sitio web / menú digital interactivo para un negocio específico.
    
    Args:
        business_name: Nombre comercial del negocio (ej. 'Café La Mina').
        niche: Giro o nicho (cafetería, restaurante, pastelería, florería, boutique, salón de eventos).
        city: Ciudad del negocio (Torreón, Gómez Palacio, Lerdo).
        phone: Teléfono para vincular los pedidos por WhatsApp.
        custom_tagline: Lema o frase personalizada opcional.
    """
    niche_key = _detect_niche_key(niche)
    template = NICHE_TEMPLATES[niche_key]
    slug = _slugify(f"{business_name}-{niche_key}")

    tagline = custom_tagline or template["tagline"]
    target_phone = "".join(filter(str.isdigit, phone)) if phone else "5218719164677"

    demo_data = {
        "slug": slug,
        "business_name": business_name,
        "niche": niche,
        "niche_key": niche_key,
        "niche_title": template["title"],
        "tagline": tagline,
        "city": city or "Comarca Lagunera",
        "phone": target_phone,
        "primary_color": template["primary_color"],
        "accent_color": template["accent_color"],
        "bg_color": template["bg_color"],
        "categories": template["categories"],
        "items": template["items"],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "agency_name": "SSSSolutions",
        "agency_instagram": "https://www.instagram.com/ssss.olutions",
        "agency_portfolio": "https://st24030217-maker.github.io/cv-salinas/"
    }

    demos = _load_all_demos()
    demos[slug] = demo_data
    _save_all_demos(demos)

    demo_url = f"/demo/{slug}"
    return {
        "success": True,
        "slug": slug,
        "url": demo_url,
        "business_name": business_name,
        "niche": niche_key,
        "city": city,
        "item_count": len(template["items"]),
        "message": f"Prototipo interactivo generado exitosamente para '{business_name}' en {demo_url}"
    }

def get_demo(slug: str) -> dict | None:
    safe_slug = re.sub(r"[^a-z0-9\-]", "", str(slug).lower().strip())[:64]
    if not safe_slug:
        return None
    demos = _load_all_demos()
    return demos.get(safe_slug)

def list_all_demos() -> list[dict]:
    demos = _load_all_demos()
    return list(demos.values())

def render_demo_html(demo: dict) -> str:
    """Renderiza el documento HTML completo del demo interactivo con carrito a WhatsApp, blindado contra XSS."""
    safe_business_name = html.escape(str(demo.get("business_name", "")), quote=True)
    safe_tagline = html.escape(str(demo.get("tagline", "")), quote=True)
    safe_city = html.escape(str(demo.get("city", "Comarca Lagunera")), quote=True)
    safe_phone = "".join(filter(str.isdigit, str(demo.get("phone", "5218719164677"))))
    safe_instagram = html.escape(str(demo.get("agency_instagram", "https://www.instagram.com/ssss.olutions")), quote=True)

    safe_primary = html.escape(str(demo.get("primary_color", "#f59e0b")), quote=True)
    safe_accent = html.escape(str(demo.get("accent_color", "#d97706")), quote=True)
    safe_bg = html.escape(str(demo.get("bg_color", "#0c0a09")), quote=True)

    safe_items = []
    for it in demo.get("items", []):
        safe_items.append({
            "id": re.sub(r"[^a-zA-Z0-9_\-]", "", str(it.get("id", ""))),
            "name": html.escape(str(it.get("name", "")), quote=True),
            "cat": html.escape(str(it.get("cat", "")), quote=True),
            "price": float(it.get("price", 0)),
            "desc": html.escape(str(it.get("desc", "")), quote=True)
        })
    def _safe_json_for_script(obj) -> str:
        return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")

    items_json = _safe_json_for_script(safe_items)

    categories_html = "".join(
        f'<button class="tab-btn" onclick="filterCategory({_safe_json_for_script(cat)})">{html.escape(str(cat))}</button>'
        for cat in demo.get("categories", [])
    )

    wa_pitch_text = urllib.parse.quote(f"Hola Sebastián, vi el demo interactivo para {demo.get('business_name', '')} y quiero activar mi sistema.")
    target_phone_json = _safe_json_for_script(safe_phone)
    business_name_json = _safe_json_for_script(str(demo.get("business_name", "")))

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>{safe_business_name} - Menú y Catálogo Digital Interactivo</title>
  <meta name="description" content="Prototipo interactivo desarrollado para {safe_business_name} por SSSSolutions.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {{
      --primary: {safe_primary};
      --accent: {safe_accent};
      --bg: {safe_bg};
      --card-bg: rgba(255, 255, 255, 0.04);
      --card-border: rgba(255, 255, 255, 0.08);
      --text: #f8fafc;
      --text-muted: #94a3b8;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-tap-highlight-color: transparent;
    }}

    body {{
      font-family: 'Plus Jakarta Sans', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
      padding-bottom: 90px;
    }}

    /* BANNER SUPERIOR DE PROTOTIPO SSSSOLUTIONS */
    .agency-top-ribbon {{
      background: linear-gradient(90deg, rgba(56, 189, 248, 0.15), rgba(99, 102, 241, 0.15));
      border-bottom: 1px solid rgba(56, 189, 248, 0.25);
      padding: 8px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.75rem;
      backdrop-filter: blur(12px);
      position: sticky;
      top: 0;
      z-index: 50;
    }}
    .agency-ribbon-left {{
      display: flex;
      align-items: center;
      gap: 6px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: #38bdf8;
    }}
    .pulse-dot {{
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #38bdf8;
      box-shadow: 0 0 8px #38bdf8;
    }}
    .agency-ribbon-link {{
      color: #ffffff;
      text-decoration: none;
      font-weight: 600;
      padding: 3px 10px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 12px;
      transition: all 0.2s;
    }}
    .agency-ribbon-link:hover {{
      background: #38bdf8;
      color: #000;
    }}

    /* HERO SECTION */
    .hero {{
      padding: 32px 20px 24px 20px;
      text-align: center;
      background: radial-gradient(circle at 50% 0%, rgba(245, 158, 11, 0.08), transparent 70%);
      border-bottom: 1px solid var(--card-border);
    }}
    .exclusive-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 14px;
      border-radius: 9999px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--card-border);
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--primary);
      margin-bottom: 12px;
    }}
    .hero h1 {{
      font-family: 'Space Grotesk', sans-serif;
      font-size: 2.2rem;
      font-weight: 800;
      line-height: 1.15;
      letter-spacing: -0.02em;
      margin-bottom: 8px;
      color: #ffffff;
    }}
    .hero p {{
      font-size: 0.95rem;
      color: var(--text-muted);
      max-width: 500px;
      margin: 0 auto 16px auto;
      line-height: 1.45;
    }}
    .location-tag {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 0.8rem;
      color: #cbd5e1;
      background: rgba(255, 255, 255, 0.03);
      padding: 4px 12px;
      border-radius: 8px;
      border: 1px solid var(--card-border);
    }}

    /* TABS DE CATEGORIAS */
    .category-tabs {{
      display: flex;
      gap: 8px;
      overflow-x: auto;
      padding: 16px 20px;
      border-bottom: 1px solid var(--card-border);
      scrollbar-width: none;
      -ms-overflow-style: none;
    }}
    .category-tabs::-webkit-scrollbar {{
      display: none;
    }}
    .tab-btn {{
      padding: 8px 16px;
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      font-family: inherit;
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;
    }}
    .tab-btn.active {{
      background: var(--primary);
      border-color: var(--primary);
      color: #000000;
      font-weight: 700;
    }}

    /* LISTA DE ITEMS */
    .items-container {{
      max-width: 720px;
      width: 100%;
      margin: 0 auto;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }}
    .item-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      transition: transform 0.2s, border-color 0.2s;
    }}
    .item-card:hover {{
      border-color: rgba(255, 255, 255, 0.18);
      transform: translateY(-2px);
    }}
    .item-details {{
      flex: 1;
      min-width: 0;
    }}
    .item-name {{
      font-size: 1rem;
      font-weight: 700;
      color: #ffffff;
      margin-bottom: 4px;
    }}
    .item-desc {{
      font-size: 0.8rem;
      color: var(--text-muted);
      line-height: 1.4;
      margin-bottom: 8px;
    }}
    .item-price {{
      font-family: 'Space Grotesk', sans-serif;
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--primary);
    }}

    .item-counter {{
      display: flex;
      align-items: center;
      gap: 10px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 4px;
    }}
    .counter-btn {{
      width: 32px;
      height: 32px;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.08);
      border: none;
      color: #ffffff;
      font-size: 1.1rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .counter-btn:hover {{
      background: var(--primary);
      color: #000;
    }}
    .counter-val {{
      font-family: 'Space Grotesk', sans-serif;
      font-weight: 700;
      font-size: 0.95rem;
      min-width: 18px;
      text-align: center;
    }}

    /* SECCION DE VALOR Y PROPUESTA DE SSSSOLUTIONS */
    .agency-pitch-card {{
      max-width: 720px;
      width: calc(100% - 40px);
      margin: 30px auto;
      background: linear-gradient(135deg, rgba(56, 189, 248, 0.08), rgba(99, 102, 241, 0.08));
      border: 1px solid rgba(56, 189, 248, 0.25);
      border-radius: 20px;
      padding: 24px;
      text-align: center;
    }}
    .agency-pitch-card h3 {{
      font-family: 'Space Grotesk', sans-serif;
      font-size: 1.25rem;
      font-weight: 800;
      color: #ffffff;
      margin-bottom: 8px;
    }}
    .agency-pitch-card p {{
      font-size: 0.86rem;
      color: #cbd5e1;
      line-height: 1.5;
      margin-bottom: 16px;
    }}
    .agency-btn-action {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: #38bdf8;
      color: #050608;
      text-decoration: none;
      font-weight: 800;
      font-size: 0.85rem;
      padding: 10px 22px;
      border-radius: 9999px;
      transition: all 0.2s;
    }}
    .agency-btn-action:hover {{
      background: #7dd3fc;
      transform: scale(1.03);
    }}

    /* BARRA FLOTANTE DE CARRITO INFERIOR */
    .cart-bar {{
      position: fixed;
      bottom: 16px;
      left: 50%;
      transform: translateX(-50%);
      width: calc(100% - 32px);
      max-width: 580px;
      background: rgba(15, 23, 42, 0.92);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 18px;
      padding: 12px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.7);
      z-index: 100;
      transition: all 0.3s ease;
    }}
    .cart-bar.empty {{
      opacity: 0.45;
      pointer-events: none;
    }}
    .cart-summary {{
      display: flex;
      flex-direction: column;
    }}
    .cart-items-count {{
      font-size: 0.72rem;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .cart-total-price {{
      font-family: 'Space Grotesk', sans-serif;
      font-size: 1.25rem;
      font-weight: 800;
      color: #ffffff;
    }}
    .cart-checkout-btn {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: #10b981;
      color: #ffffff;
      border: none;
      padding: 10px 20px;
      border-radius: 12px;
      font-family: inherit;
      font-size: 0.9rem;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s;
      white-space: nowrap;
    }}
    .cart-checkout-btn:hover {{
      background: #059669;
      transform: scale(1.02);
    }}
  </style>
</head>
<body>

  <!-- RIBBON DE IDENTIDAD DE AGENCIA -->
  <div class="agency-top-ribbon">
    <div class="agency-ribbon-left">
      <span class="pulse-dot"></span>
      <span>Prototipo Activo SSSSolutions</span>
    </div>
    <a href="{safe_instagram}" target="_blank" class="agency-ribbon-link">
      @ssss.olutions
    </a>
  </div>

  <!-- HERO SECTION -->
  <section class="hero">
    <div class="exclusive-badge">
      <span>Demo Exclusivo para</span>
      <span>{safe_business_name}</span>
    </div>
    <h1>{safe_business_name}</h1>
    <p>{safe_tagline}</p>
    <div class="location-tag">
      <span>Ubicación:</span>
      <strong>{safe_city}</strong>
    </div>
  </section>

  <!-- FILTRO DE CATEGORIAS -->
  <div class="category-tabs">
    <button class="tab-btn active" onclick="filterCategory('all')">Todos</button>
    {categories_html}
  </div>

  <!-- ITEMS DEL MENU / CATALOGO -->
  <main class="items-container" id="items-list">
    <!-- Renderizado por JS -->
  </main>

  <!-- PROPUESTA DE VALOR SSSSOLUTIONS -->
  <section class="agency-pitch-card">
    <h3>¿Quieres este sistema activo para tu negocio?</h3>
    <p>
      Este prototipo interactivo fue diseñado a la medida por <strong>SSSSolutions</strong>. 
      Digitalizamos tu catálogo, optimizamos pedidos directos por WhatsApp sin comisiones y aumentamos tus ventas en La Laguna.
    </p>
    <a href="https://wa.me/{safe_phone}?text={wa_pitch_text}" class="agency-btn-action" target="_blank">
      Contactar a SSSSolutions
    </a>
  </section>

  <!-- BARRA DE CARRITO INFERIOR -->
  <div class="cart-bar empty" id="cart-bar">
    <div class="cart-summary">
      <span class="cart-items-count" id="cart-count-label">0 productos seleccionados</span>
      <span class="cart-total-price" id="cart-total-label">$0.00 MXN</span>
    </div>
    <button class="cart-checkout-btn" onclick="checkoutWhatsApp()">
      Pedir por WhatsApp
    </button>
  </div>

  <script>
    const itemsData = {items_json};
    const cart = {{}};
    const targetPhone = {target_phone_json};
    const businessName = {business_name_json};

    function renderItems(filter = "all") {{
      const container = document.getElementById("items-list");
      if (!container) return;

      const filtered = filter === "all" 
        ? itemsData 
        : itemsData.filter(i => i.cat === filter);

      container.innerHTML = filtered.map(item => {{
        const qty = cart[item.id] || 0;
        return `
          <div class="item-card">
            <div class="item-details">
              <div class="item-name">${{item.name}}</div>
              <div class="item-desc">${{item.desc}}</div>
              <div class="item-price">$${{item.price}} MXN</div>
            </div>
            <div class="item-counter">
              <button class="counter-btn" onclick="updateQty('${{item.id}}', -1)">-</button>
              <span class="counter-val" id="qty-${{item.id}}">${{qty}}</span>
              <button class="counter-btn" onclick="updateQty('${{item.id}}', 1)">+</button>
            </div>
          </div>
        `;
      }}).join("");
    }}

    function filterCategory(cat) {{
      document.querySelectorAll(".tab-btn").forEach(btn => {{
        if ((cat === "all" && btn.textContent === "Todos") || btn.textContent === cat) {{
          btn.classList.add("active");
        }} else {{
          btn.classList.remove("active");
        }}
      }});
      renderItems(cat);
    }}

    function updateQty(id, delta) {{
      const current = cart[id] || 0;
      const next = Math.max(0, current + delta);
      if (next === 0) {{
        delete cart[id];
      }} else {{
        cart[id] = next;
      }}
      const el = document.getElementById("qty-" + id);
      if (el) el.textContent = next;
      updateCartBar();
    }}

    function updateCartBar() {{
      const bar = document.getElementById("cart-bar");
      const countLabel = document.getElementById("cart-count-label");
      const totalLabel = document.getElementById("cart-total-label");

      let totalItems = 0;
      let totalPrice = 0;

      for (const [id, qty] of Object.entries(cart)) {{
        const item = itemsData.find(i => i.id === id);
        if (item) {{
          totalItems += qty;
          totalPrice += item.price * qty;
        }}
      }}

      if (totalItems > 0) {{
        bar.classList.remove("empty");
        countLabel.textContent = totalItems + (totalItems === 1 ? " producto seleccionado" : " productos seleccionados");
        totalLabel.textContent = "$" + totalPrice.toLocaleString("es-MX") + " MXN";
      }} else {{
        bar.classList.add("empty");
        countLabel.textContent = "0 productos seleccionados";
        totalLabel.textContent = "$0.00 MXN";
      }}
    }}

    function checkoutWhatsApp() {{
      let orderLines = [];
      let total = 0;

      for (const [id, qty] of Object.entries(cart)) {{
        const item = itemsData.find(i => i.id === id);
        if (item) {{
          const subtotal = item.price * qty;
          total += subtotal;
          orderLines.push(`${{qty}}x ${{item.name}} ($${{subtotal}} MXN)`);
        }}
      }}

      if (orderLines.length === 0) return;

      const message = `Hola ${{businessName}}, quiero realizar el siguiente pedido visto en su menú interactivo:\n\n` +
        orderLines.join("\n") +
        `\n\nTotal: $${{total}} MXN\n\nMi nombre es: \nDirección de entrega: `;

      const waUrl = `https://wa.me/${{targetPhone}}?text=${{encodeURIComponent(message)}}`;
      window.open(waUrl, "_blank");
    }}

    renderItems("all");
  </script>
</body>
</html>"""
