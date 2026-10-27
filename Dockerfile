# Imagen base oficial de Python 3.12
FROM python:3.12-slim-bookworm

# Evitar prompts interactivos durante instalación
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Instalar dependencias del sistema, Node.js 22 y supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    build-essential \
    supervisor \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar dependencias de Python y configuraciones
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi==0.162.0 \
    uvicorn==0.54.0 \
    google-genai==2.33.0 \
    pydantic==2.14.1 \
    python-dotenv==1.2.4 \
    httpx==0.28.1 \
    beautifulsoup4==4.15.0 \
    ddgs==9.16.1 \
    edge-tts==7.3.1 \
    truststore==0.10.5

# Copiar dependencias de Node.js del conector de WhatsApp
COPY bridge/package*.json ./bridge/
RUN cd bridge && npm install --no-audit --no-fund

# Copiar todo el código fuente del proyecto
COPY . .

# Instalar paquete local del agente
RUN pip install --no-cache-dir -e .

# Configurar supervisor para gestionar FastAPI y el bridge de WhatsApp 24/7
RUN mkdir -p /var/log/supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Puerto principal de la aplicación web y webhook
EXPOSE 8000

# Punto de entrada para ejecutar ambos servicios concurrentemente
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
