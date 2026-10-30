# Guía de Operación 24/7 para Sebax (SSSSolutions)

Para que Sebax esté funcionando las 24 horas del día, los 7 días de la semana, respondiendo en WhatsApp, prospectando negocios y atendiendo en tu app móvil, dispones de dos modalidades:

---

## Opción 1: En tu computadora actual (Inmediato y sin costo)

Tu repositorio ya cuenta con un **Guardián Supervisor 24/7** (`supervisor.py`) que:
1. Mantiene activos en segundo plano FastAPI, el conector de WhatsApp y Cloudflare Tunnel.
2. Si cualquiera de los 3 se cierra o falla, lo reinicia automáticamente en menos de 4 segundos.
3. Evita que Windows entre en modo de suspensión o suspenda procesos en segundo plano.
4. Funciona en modo 100% invisible (sin ventanas negras estorbando).

### Cómo activarlo para que inicie solo al prender tu PC:
1. Abre PowerShell en la carpeta del proyecto y ejecuta:
   ```powershell
   .\setup_autostart.ps1
   ```
2. Esto creará un acceso directo en tu carpeta de inicio de Windows. Cada vez que enciendas o reinicies tu computadora, Sebax arrancará solo en segundo plano.
3. Para iniciarlo manualmente en cualquier momento sin ventanas visibles, solo da doble clic a:
   `start_24_7.vbs`

---

## Opción 2: En la nube (Sin depender de tu computadora)

Si deseas apagar tu computadora por completo o viajar sin ella y que Sebax siga vivo 365 días al año en internet:

### A. Despliegue en Railway.app (Recomendado)
1. Sube los cambios a tu repositorio de GitHub:
   ```bash
   git add .
   git commit -m "Add 24/7 Docker and supervisor"
   git push origin main
   ```
2. Entra en [Railway.app](https://railway.app/) e inicia sesión con tu GitHub (`st24030217-maker`).
3. Crea un **New Project** > **Deploy from GitHub repo** > selecciona `agente`.
4. En **Variables**, agrega:
   - `GEMINI_API_KEY`: tu clave de Google Gemini
   - `GEMINI_MODEL`: `gemini-3.5-flash-lite`
5. En **Settings** > **Volumes**, añade un volumen persistente montado en `/app/bridge/auth_info_baileys` y `/app/data` para que tu sesión de WhatsApp y tus prospectos nunca se borren.
6. Railway generará un dominio público HTTPS `https://...up.railway.app` activo 24/7.

### B. Despliegue en Render

Render usa almacenamiento efímero por defecto. Sin un disco persistente, un reinicio o despliegue puede borrar las credenciales de WhatsApp y solicitar un QR nuevo.

1. Despliega la versión actual del repositorio como servicio Docker y configura `GEMINI_API_KEY` y `GEMINI_MODEL=gemini-3.5-flash-lite`.
2. En **Settings > Disks**, crea un disco persistente montado en `/var/data`. Los discos persistentes requieren un tipo de instancia de Render que los admita.
3. En **Environment**, configura:
   - `WHATSAPP_AUTH_DIR=/var/data/whatsapp-auth`
   - `DATA_DIR=/var/data/data`
4. Guarda los cambios y espera a que termine el despliegue.
5. Abre **Conectar WhatsApp** y escanea de nuevo el QR una sola vez. Confirma que `/api/bridge/status` reporte `"status":"open"` y un usuario vinculado.

La sesión vinculada antes de montar el disco puede haberse perdido. Si Render muestra `qr_ready`, hay que volver a escanear después de configurar el almacenamiento persistente.

### C. Despliegue en un VPS Linux (Ubuntu 24.04 / Hetzner / DigitalOcean / Hostinger)
1. Conéctate a tu servidor por SSH.
2. Clona el repositorio:
   ```bash
   git clone https://github.com/st24030217-maker/agente.git
   cd agente
   ```
3. Crea tu archivo `.env` con tu `GEMINI_API_KEY`.
4. Inicia con Docker Compose:
   ```bash
   docker compose up -d --build
   ```
5. El contenedor correrá indefinidamente gestionado por `supervisord`.

---

## Resumen de enlaces oficiales utilizados por Sebax

- **Portafolio oficial**: https://st24030217-maker.github.io/cv-salinas/
- **Instagram de negocio**: https://www.instagram.com/ssss.olutions
