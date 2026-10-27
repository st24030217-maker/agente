# 🤖 Agente Personal de IA (WhatsApp & CLI)

Un agente de Inteligencia Artificial personal diseñado para acompañarte en tus tareas diarias, apoyo en desarrollo, ejecución de scripts de terminal, revisión de archivos y gestión de notas/pendientes, integrado directamente con **WhatsApp** y potenciado por **Google Gemini**.

---

## 🚀 Inicio Rápido (En corto)

### 1. Configurar tu clave de Google Gemini
1. Obtén tu API key gratuita en [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Abre el archivo `.env` en la raíz del proyecto y coloca tu clave:
   ```env
   GEMINI_API_KEY=tu_clave_de_gemini_aqui
   ```

### 2. Iniciar el agente y WhatsApp
Ejecuta en tu terminal PowerShell:
```powershell
.\start.ps1
```
Esto abrirá dos ventanas:
- **Agente Python (puerto 8000)**: Procesa la lógica, herramientas y modelos de IA.
- **WhatsApp Bridge (puerto 3000)**: Conector de WhatsApp Web.

### 3. Vincular WhatsApp
1. Abre en tu navegador: [http://localhost:3000/qr](http://localhost:3000/qr) (o míralo en la consola).
2. Abre WhatsApp en tu celular > **Dispositivos vinculados** > **Vincular un dispositivo** y escanea el código.
3. ¡Listo! Puedes enviarle un mensaje desde tu WhatsApp y el agente te responderá en corto.

---

## 🛠️ Modos de Ejecución

- **Modo Completo (WhatsApp + Agente)**:
  ```powershell
  .\start.ps1
  ```
- **Modo CLI Interactivo (Directo en consola, sin WhatsApp)**:
  ```powershell
  .\start.ps1 -Mode cli
  ```
- **Solo servidor de Agente**:
  ```powershell
  .\start.ps1 -Mode agent
  ```
- **Solo conector de WhatsApp**:
  ```powershell
  .\start.ps1 -Mode bridge
  ```

---

## 🧠 Capacidades y Herramientas del Agente

El agente cuenta con herramientas integradas ("Function Calling") que ejecuta automáticamente según lo que le pidas:

1. **Terminal & Scripts (`run_command`)**:
   - Ejecuta comandos de PowerShell de forma segura (ej. `git status`, `python main.py`, `npm test`, etc.).
2. **Explorador de Archivos (`read_file`, `write_file`, `list_directory`)**:
   - Lee y edita código o archivos de tus proyectos.
3. **Gestor de Notas y Pendientes Diarios (`add_note_or_task`, `list_notes_and_tasks`, `delete_note_or_task`)**:
   - Guarda ideas, recordatorios y tareas pendientes que persisten en `data/notes.json`.
4. **Comandos Especiales en el Chat**:
   - `/reset` o `/clear`: Reinicia la memoria de la conversación actual.

---

## 🔒 Seguridad y Privacidad

- **Filtrado de números**: Si deseas que el agente **solo** te responda a ti o a números específicos, configura en `.env`:
  ```env
  ALLOWED_NUMBERS=521XXXXXXXXXX,521YYYYYYYYYY
  ```
- Tu sesión de WhatsApp se almacena localmente en la carpeta `bridge/auth_info_baileys/` y está excluida de Git en `.gitignore`.
