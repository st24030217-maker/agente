import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS

def search_web(query: str, max_results: int = 5) -> str:
    """Busca en internet información actualizada, documentación, soluciones a errores o código.
    
    Args:
        query: Consulta de búsqueda (ej. 'FastAPI lifespan events documentation', 'Error pip SSL certifi').
        max_results: Número de resultados a devolver (máximo 5).
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return f"No se encontraron resultados en la web para: '{query}'."

        formatted = [f"Resultados de búsqueda web para: '{query}':\n"]
        for i, item in enumerate(results, 1):
            title = item.get("title", "Sin título")
            body = item.get("body", "")
            href = item.get("href", "")
            formatted.append(f"{i}. *{title}*\n   {body}\n   Fuente: {href}\n")

        return "\n".join(formatted)
    except Exception as e:
        return f"Error al buscar en la web: {str(e)}"

def fetch_web_content(url: str, max_chars: int = 3500) -> str:
    """Lee y extrae el contenido de texto principal de una página web o documentación.
    
    Args:
        url: La dirección URL a consultar (ej. 'https://docs.python.org/3/whatsnew/3.12.html').
        max_chars: Límite de caracteres para no saturar el contexto del agente.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        with httpx.Client(timeout=15.0, follow_redirects=True, verify=False) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Eliminar scripts, estilos y elementos no informativos
        for elem in soup(["script", "style", "nav", "footer", "header", "aside"]):
            elem.extract()

        text = soup.get_text(separator="\n", strip=True)
        # Limpiar saltos de línea repetidos
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned = "\n".join(lines)

        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars] + f"\n\n... (contenido truncado a {max_chars} caracteres)"

        return f"Contenido extraído de {url}:\n\n{cleaned}"
    except Exception as e:
        return f"Error al acceder a '{url}': {str(e)}"
