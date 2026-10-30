import express from "express";
import qrcodeTerminal from "qrcode-terminal";
import QRCode from "qrcode";
import dotenv from "dotenv";
import {
  makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
  Browsers,
  areJidsSameUser
} from "@whiskeysockets/baileys";
import pino from "pino";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, "..");

dotenv.config({ path: path.resolve(__dirname, "../.env") });

const PORT = process.env.BRIDGE_PORT || 3000;
const AGENT_WEBHOOK_URL = process.env.AGENT_WEBHOOK_URL || "http://127.0.0.1:8000/webhook/whatsapp";
const authFolderSetting = process.env.WHATSAPP_AUTH_DIR || path.join(__dirname, "auth_info_baileys");
const AUTH_FOLDER = path.isAbsolute(authFolderSetting)
  ? authFolderSetting
  : path.resolve(PROJECT_ROOT, authFolderSetting);

async function callFastAPI(endpoint, body) {
  const candidatePorts = [
    process.env.PORT ? Number(process.env.PORT) : null,
    8000,
    10000
  ].filter(p => typeof p === "number" && !isNaN(p) && p > 0);
  const uniquePorts = [...new Set(candidatePorts)];

  for (const p of uniquePorts) {
    try {
      const url = `http://127.0.0.1:${p}${endpoint}`;
      console.log(`[callFastAPI] POST a ${url}...`);
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(180000)
      });
      if (res.ok) {
        const json = await res.json();
        console.log(`[callFastAPI] Exito en ${url}`);
        return json;
      } else {
        console.warn(`[callFastAPI] Status HTTP ${res.status} desde ${url}`);
      }
    } catch (e) {
      console.warn(`[callFastAPI] Puerto ${p} falló: ${e.message}`);
    }
  }
  console.error(`[callFastAPI] Ningun puerto respondio (${uniquePorts.join(", ")})`);
  return null;
}

const app = express();
app.use(express.json());

let currentQR = null;
let connectionState = "starting";
let sock = null;
const botSentMessageIds = new Set();
const processedIncomingMessageIds = new Set();
const messageStatusById = new Map();
const deliveryStatusWaiters = new Map();

function getDeliveryStatusName(status) {
  return ({ 0: "error", 1: "pending", 2: "server_ack", 3: "delivery_ack", 4: "read", 5: "played" })[status] || "unknown";
}

function waitForDeliveryStatus(messageId, timeoutMs = 15000) {
  if (!messageId) return Promise.resolve(null);

  const currentStatus = messageStatusById.get(messageId);
  if (currentStatus === 0 || currentStatus >= 3) {
    return Promise.resolve(currentStatus);
  }

  return new Promise(resolve => {
    const timeout = setTimeout(() => {
      deliveryStatusWaiters.delete(messageId);
      resolve(messageStatusById.get(messageId) ?? null);
    }, timeoutMs);

    deliveryStatusWaiters.set(messageId, status => {
      clearTimeout(timeout);
      deliveryStatusWaiters.delete(messageId);
      resolve(status);
    });
  });
}

function normalizePhone(phone) {
  let clean = (phone || "").toString().replace(/\D/g, "");
  if (clean.length === 10) {
    clean = "52" + clean;
  } else if (clean.length === 13 && clean.startsWith("521")) {
    clean = "52" + clean.slice(3);
  }
  return clean;
}

function getPhoneJidCandidates(phone) {
  const digits = (phone || "").toString().replace(/\D/g, "");
  const candidates = new Set([normalizePhone(digits)]);

  if (digits.length === 10) {
    candidates.add(`521${digits}`);
  } else if (digits.length === 12 && digits.startsWith("52")) {
    candidates.add(`521${digits.slice(2)}`);
  } else if (digits.length === 13 && digits.startsWith("521")) {
    candidates.add(`52${digits.slice(3)}`);
  }

  return [...candidates].filter(Boolean).map(number => `${number}@s.whatsapp.net`);
}

async function resolveRecipientJid(destination) {
  if (!destination || destination.endsWith("@lid") || destination.endsWith("@g.us")) {
    return destination;
  }

  const number = destination.includes("@")
    ? destination.split("@")[0].split(":")[0]
    : destination;
  const candidates = getPhoneJidCandidates(number);
  if (!candidates.length) {
    throw new Error("No se pudo identificar el número de WhatsApp destinatario.");
  }

  const matches = await sock.onWhatsApp(...candidates);
  const match = matches?.find(result => result.exists && result.jid);
  if (!match) {
    throw new Error("El número indicado no aparece registrado en WhatsApp.");
  }

  const resolvedJid = match.jid;
  console.log(`[Destinatario resuelto por WhatsApp: ${match.jid}; LID: ${match.lid || "no disponible"}]`);
  return resolvedJid;
}

function isSelfUser(jid) {
  if (!jid) return false;
  const digits = jid.split("@")[0].replace(/\D/g, "");
  if (digits.includes("8719164677")) return true;
  if (!sock || !sock.user) return false;
  try {
    if (areJidsSameUser(jid, sock.user.id)) return true;
    if (sock.user.lid && areJidsSameUser(jid, sock.user.lid)) return true;
  } catch (e) {}

  const d1 = jid.split("@")[0].replace(/\D/g, "");
  const d2 = (sock.user.id || "").split("@")[0].replace(/\D/g, "");
  if (d1.length >= 8 && d2.length >= 8) {
    if (d1.endsWith(d2.slice(-8)) || d2.endsWith(d1.slice(-8))) {
      return true;
    }
  }
  return false;
}

async function getMessageRecipientJid(msg) {
  const phoneJid = msg.key.senderPn || msg.key.participantPn;
  if (phoneJid) {
    return resolveRecipientJid(phoneJid);
  }
  return msg.key.remoteJid;
}

function getDiagnosticReply(message) {
  const normalized = message
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase();

  if (/^(prueba|test|diagnostico)\b/.test(normalized)) {
    return "Recibí tu mensaje de prueba. El canal de WhatsApp está activo; este mensaje no ejecuta herramientas comerciales.";
  }

  if (/^(hola|hey|buenas|buenos dias|buenas tardes|buenas noches)[.!?]*$/.test(normalized)) {
    return "Hola. Recibí tu mensaje por WhatsApp y estoy listo para ayudarte.";
  }

  return "";
}

app.get("/status", (req, res) => {
  res.json({
    status: connectionState,
    has_qr: !!currentQR,
    user: sock?.user ? { id: sock.user.id, name: sock.user.name } : null
  });
});

app.get("/qr-data", async (req, res) => {
  if (connectionState === "open") {
    return res.json({ status: "open", qr: null, user: sock?.user?.id || null });
  }
  if (!currentQR) {
    return res.json({ status: connectionState, qr: null });
  }
  try {
    const dataUrl = await QRCode.toDataURL(currentQR, { width: 300, margin: 2 });
    res.json({ status: connectionState, qr: dataUrl });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post("/pairing-code", async (req, res) => {
  try {
    const rawPhone = req.body?.phone || "8719164677";
    let clean = normalizePhone(rawPhone);
    if (clean.length < 10) {
      return res.status(400).json({ error: "Número no válido. Ingresa tu número de 10 dígitos (ej. 8719164677)." });
    }
    if (!sock) {
      return res.status(503).json({ error: "El conector de WhatsApp está arrancando. Intenta en 5 segundos." });
    }
    if (connectionState === "open") {
      return res.json({ already_connected: true });
    }

    let rawCode;
    try {
      rawCode = await sock.requestPairingCode(clean);
    } catch (pairErr) {
      console.warn("Fallo con formato", clean, pairErr.message, "- Intentando alternativa...");
      if (clean.startsWith("52") && !clean.startsWith("521")) {
        const altDigits = "521" + clean.slice(2);
        rawCode = await sock.requestPairingCode(altDigits);
      } else {
        throw pairErr;
      }
    }
    const formattedCode = rawCode ? rawCode.match(/.{1,4}/g)?.join("-") || rawCode : "";
    res.json({ success: true, code: formattedCode });
  } catch (err) {
    console.error("Error al generar código de vinculación:", err.message);
    res.status(500).json({ error: err.message || "No se pudo generar el código. Verifica el número e intenta nuevamente." });
  }
});

app.post("/reset", async (req, res) => {
  try {
    try {
      fs.rmSync(AUTH_FOLDER, { recursive: true, force: true });
    } catch (e) {}
    connectionState = "starting";
    currentQR = null;
    startWhatsApp();
    res.json({ success: true, message: "Sesión reiniciada. Generando nuevo código..." });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get("/qr", async (req, res) => {
  let initialQr = "";
  if (currentQR) {
    try {
      initialQr = await QRCode.toDataURL(currentQR, { width: 300, margin: 2 });
    } catch (e) {}
  }

  res.send(`
    <!DOCTYPE html>
    <html lang="es">
    <head>
      <title>Vincular WhatsApp | SSSSolutions</title>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
      <link rel="preconnect" href="https://fonts.googleapis.com">
      <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@600;800&display=swap" rel="stylesheet">
      <style>
        * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
        body {
          font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
          display: flex; align-items: center; justify-content: center;
          min-height: 100vh; min-height: 100dvh;
          background: #f8fafc; color: #09090b;
          padding: 20px; padding-top: max(20px, env(safe-area-inset-top)); padding-bottom: max(20px, env(safe-area-inset-bottom));
        }
        .container {
          width: 100%; max-width: 440px; margin: 0 auto;
        }
        .card {
          background: #ffffff;
          border-radius: 28px;
          border: 1px solid rgba(0,0,0,0.08);
          box-shadow: 0 20px 48px -12px rgba(0,0,0,0.05);
          padding: 2.2rem 1.8rem;
          text-align: center;
        }
        .brand {
          font-size: 0.72rem; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase;
          color: #71717a; margin-bottom: 0.5rem;
        }
        h1 {
          font-size: 1.35rem; font-weight: 800; letter-spacing: -0.4px; color: #09090b; margin-bottom: 0.35rem;
        }
        p.subtitle {
          font-size: 0.82rem; color: #71717a; line-height: 1.45; margin-bottom: 1.4rem;
        }
        .nav-tabs {
          display: flex; gap: 6px; background: #f1f5f9; padding: 4px; border-radius: 14px; margin-bottom: 1.4rem;
        }
        .tab-btn {
          flex: 1; border: none; background: transparent; padding: 9px 12px; font-size: 0.78rem;
          font-weight: 600; color: #64748b; border-radius: 10px; cursor: pointer; transition: all 0.2s;
        }
        .tab-btn.active {
          background: #ffffff; color: #09090b; box-shadow: 0 2px 8px rgba(0,0,0,0.06); font-weight: 700;
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }

        .input-group {
          margin-bottom: 1rem; text-align: left;
        }
        .input-label {
          font-size: 0.74rem; font-weight: 700; color: #3f3f46; margin-bottom: 6px; display: block;
        }
        .phone-input {
          width: 100%; padding: 13px 16px; border-radius: 14px; border: 1.5px solid #e2e8f0;
          font-size: 0.95rem; font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 600; color: #09090b;
          outline: none; transition: border-color 0.2s; background: #ffffff;
        }
        .phone-input:focus {
          border-color: #09090b;
        }
        .btn-action {
          width: 100%; border: none; background: #09090b; color: #ffffff; font-weight: 700;
          font-size: 0.88rem; padding: 14px 18px; border-radius: 14px; cursor: pointer;
          transition: opacity 0.2s; font-family: 'Plus Jakarta Sans', sans-serif;
        }
        .btn-action:hover { opacity: 0.9; }
        .btn-action:disabled { opacity: 0.5; cursor: not-allowed; }

        .code-display {
          margin: 1.2rem 0; padding: 16px; background: #f8fafc; border: 1.5px dashed #cbd5e1;
          border-radius: 16px; text-align: center; display: none;
        }
        .code-number {
          font-family: 'JetBrains Mono', monospace; font-size: 1.7rem; font-weight: 800;
          letter-spacing: 3px; color: #09090b; margin-bottom: 8px; user-select: all;
        }
        .btn-copy {
          background: #e2e8f0; border: none; border-radius: 8px; padding: 6px 14px;
          font-size: 0.72rem; font-weight: 700; color: #334155; cursor: pointer;
        }

        .qr-box {
          background: #ffffff; padding: 14px; border-radius: 20px; display: inline-block;
          border: 1px solid rgba(0,0,0,0.08); box-shadow: 0 8px 24px rgba(0,0,0,0.04); margin-bottom: 1.2rem;
        }
        .qr-box img { display: block; border-radius: 12px; max-width: 100%; height: auto; margin: 0 auto; }

        .steps-box {
          text-align: left; background: #f8fafc; border-radius: 16px;
          padding: 14px 16px; font-size: 0.77rem; color: #3f3f46; line-height: 1.55;
          border: 1px solid rgba(0,0,0,0.04); margin-top: 1.2rem;
        }
        .steps-box ol { padding-left: 18px; margin: 0; }
        .steps-box li { margin-bottom: 4px; }
        .steps-box li:last-child { margin-bottom: 0; }

        .connected-state {
          display: none; padding: 1.5rem 0;
        }
        .badge-live {
          display: inline-flex; align-items: center; gap: 6px; padding: 6px 16px; border-radius: 20px;
          background: #ecfdf5; color: #059669; font-weight: 700; font-size: 0.78rem;
          text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 1.2rem;
        }
        .dot { width: 8px; height: 8px; border-radius: 50%; background: #10b981; }

        .footer-note {
          margin-top: 1.4rem; font-size: 0.72rem; font-weight: 600; color: #a1a1aa; text-align: center;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="card" id="mainCard">
          <div class="brand">SSSSolutions • Sebax</div>

          <!-- Estado Conectado -->
          <div id="connectedView" class="connected-state">
            <div class="badge-live"><span class="dot"></span> En Linea y Operativo</div>
            <h1 style="margin-bottom:0.6rem;">WhatsApp Conectado con Exito</h1>
            <p class="subtitle" id="connectedUserText">Sebax esta operando 24/7 en Torreon, Gomez Palacio y Lerdo atendiendo y prospectando clientes.</p>
            <div class="steps-box" style="text-align:center; background:#ecfdf5; border-color:#a7f3d0; color:#065f46;">
              Tus prospectos pendientes se enviaran automaticamente. Ya puedes cerrar esta ventana.
            </div>
          </div>

          <!-- Estado Desconectado / Vinculacion -->
          <div id="pairingView">
            <h1>Vincular WhatsApp</h1>
            <p class="subtitle">Conecta a Sebax para prospeccion y atencion continua 24/7.</p>

            <div class="nav-tabs">
              <button class="tab-btn active" id="tabCodeBtn" onclick="switchTab('code')">Codigo Telefonico</button>
              <button class="tab-btn" id="tabQrBtn" onclick="switchTab('qr')">Escanear QR</button>
            </div>

            <!-- TAB 1: CODIGO DE EMPAREJAMIENTO (IDEAL MOVIL) -->
            <div id="tabCode" class="tab-content active">
              <div class="input-group">
                <label class="input-label" for="phone">Numero de WhatsApp</label>
                <input type="tel" id="phone" class="phone-input" value="8719164677" placeholder="8719164677" autocomplete="tel">
              </div>
              <button class="btn-action" id="btnRequestCode" onclick="requestCode()">Obtener Codigo de 8 Digitos</button>

              <div id="codeResult" class="code-display">
                <div style="font-size:0.75rem; color:#64748b; font-weight:600; margin-bottom:6px;">Tu codigo de vinculacion:</div>
                <div class="code-number" id="pairingCodeDisplay">----</div>
                <button class="btn-copy" onclick="copyCode()">Copiar Codigo</button>
              </div>

              <div class="steps-box">
                <div style="font-weight:700; margin-bottom:4px; color:#09090b;">Instrucciones para celular:</div>
                <ol>
                  <li>Abre <b>WhatsApp</b> en tu telefono</li>
                  <li>Ve a <b>Ajustes</b> &gt; <b>Dispositivos vinculados</b> &gt; <b>Vincular un dispositivo</b></li>
                  <li>Toca abajo: <b>Vincular con el numero de telefono</b></li>
                  <li>Ingresa el codigo de 8 digitos que aparezca arriba</li>
                </ol>
              </div>
            </div>

            <!-- TAB 2: CODIGO QR (PARA PANTALLA COMPUTADORA) -->
            <div id="tabQr" class="tab-content">
              <div class="qr-box">
                <img id="qrImage" src="${initialQr || ''}" alt="Codigo QR WhatsApp" style="${initialQr ? '' : 'display:none;'}">
                <div id="qrPlaceholder" style="padding:40px 20px; font-size:0.82rem; color:#71717a; ${initialQr ? 'display:none;' : ''}">
                  Generando codigo QR seguro...
                </div>
              </div>

              <div class="steps-box">
                <div style="font-weight:700; margin-bottom:4px; color:#09090b;">Si tienes esta pagina en tu computadora:</div>
                <ol>
                  <li>Abre <b>WhatsApp</b> en tu celular</li>
                  <li>Ve a <b>Ajustes</b> &gt; <b>Dispositivos vinculados</b></li>
                  <li>Toca <b>Vincular un dispositivo</b> y apunta la camara a la pantalla</li>
                </ol>
              </div>
            </div>
          </div>

          <div class="footer-note">SSSSolutions • @ssss.olutions</div>
        </div>
      </div>

      <script>
        let currentTab = 'code';

        function switchTab(tab) {
          currentTab = tab;
          document.getElementById('tabCodeBtn').classList.toggle('active', tab === 'code');
          document.getElementById('tabQrBtn').classList.toggle('active', tab === 'qr');
          document.getElementById('tabCode').classList.toggle('active', tab === 'code');
          document.getElementById('tabQr').classList.toggle('active', tab === 'qr');
        }

        async function requestCode() {
          const phoneInput = document.getElementById('phone');
          const phone = phoneInput.value.trim();
          const btn = document.getElementById('btnRequestCode');
          const codeResult = document.getElementById('codeResult');
          const display = document.getElementById('pairingCodeDisplay');

          if (!phone) {
            alert('Por favor ingresa tu numero de telefono con clave lada.');
            phoneInput.focus();
            return;
          }

          btn.disabled = true;
          btn.textContent = 'Generando codigo...';

          try {
            const res = await fetch('/pairing-code', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ phone })
            });
            const data = await res.json();

            if (data.already_connected) {
              setConnectedView(null);
              return;
            }

            if (data.success && data.code) {
              display.textContent = data.code;
              codeResult.style.display = 'block';
              btn.textContent = 'Generar Nuevo Codigo';
            } else {
              alert(data.error || 'Error al generar el codigo de vinculacion.');
              btn.textContent = 'Reintentar';
            }
          } catch (e) {
            alert('Error de conexion: ' + e.message);
            btn.textContent = 'Reintentar';
          } finally {
            btn.disabled = false;
          }
        }

        function copyCode() {
          const display = document.getElementById('pairingCodeDisplay');
          const clean = display.textContent.replace(/-/g, '').trim();
          navigator.clipboard.writeText(clean).then(() => {
            alert('Codigo copiado al portapapeles: ' + clean);
          }).catch(() => {
            prompt('Copia este codigo:', clean);
          });
        }

        function setConnectedView(user) {
          document.getElementById('pairingView').style.display = 'none';
          document.getElementById('connectedView').style.display = 'block';
          if (user) {
            document.getElementById('connectedUserText').textContent = 'Sesión conectada a ' + user + '. La conexión está activa en este momento.';
          }
        }

        // Sondeo silencioso para detectar conexion y refrescar QR
        async function pollStatus() {
          try {
            const res = await fetch('/status');
            const data = await res.json();
            if (data.status === 'open') {
              setConnectedView(data.user?.id || null);
              return;
            }

            if (currentTab === 'qr') {
              const qrRes = await fetch('/qr-data');
              const qrData = await qrRes.json();
              if (qrData.status === 'open') {
                setConnectedView(qrData.user || null);
                return;
              }
              if (qrData.qr) {
                const img = document.getElementById('qrImage');
                const placeholder = document.getElementById('qrPlaceholder');
                img.src = qrData.qr;
                img.style.display = 'block';
                placeholder.style.display = 'none';
              }
            }
          } catch (e) {}

          setTimeout(pollStatus, 3500);
        }

        pollStatus();
      </script>
    </body>
    </html>
  `);
});

// Endpoint para que el Agente pueda enviar mensajes de WhatsApp
app.post("/send", async (req, res) => {
  const { to, text } = req.body;
  if (!sock || connectionState !== "open") {
    return res.status(503).json({ error: "WhatsApp no esta conectado actualmente." });
  }
  if (!text) {
    return res.status(400).json({ error: "El texto del mensaje no puede estar vacio." });
  }
  try {
    const jid = to ? await resolveRecipientJid(to) : sock.user.id;
    const sent = await sock.sendMessage(jid, { text });
    if (sent?.key?.id) {
      botSentMessageIds.add(sent.key.id);
    }
    console.log(`[Mensaje aceptado por el socket para ${jid}; id: ${sent?.key?.id || "desconocido"}]`);
    const deliveryStatus = await waitForDeliveryStatus(sent?.key?.id);
    const delivered = deliveryStatus === 3 || deliveryStatus === 4 || deliveryStatus === 5;
    res.json({
      accepted: true,
      delivered,
      delivery_status: getDeliveryStatusName(deliveryStatus),
      message_id: sent?.key?.id || null,
      jid
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

async function startWhatsApp() {
  fs.mkdirSync(AUTH_FOLDER, { recursive: true });
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_FOLDER);
  const { version } = await fetchLatestBaileysVersion();

  sock = makeWASocket({
    version,
    logger: pino({ level: "silent" }),
    printQRInTerminal: false,
    auth: state,
    browser: Browsers.macOS("Desktop"),
    syncFullHistory: false,
    markOnlineOnConnect: true,
    connectTimeoutMs: 60000,
    defaultQueryTimeoutMs: 0,
    keepAliveIntervalMs: 15000,
    generateHighQualityLinkPreview: false,
    getMessage: async () => undefined
  });

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      currentQR = qr;
      connectionState = "qr_ready";
      console.log("\n CODIGO QR GENERADO: http://localhost:" + PORT + "/qr\n");
      qrcodeTerminal.generate(qr, { small: true });
    }

    if (connection === "close") {
      connectionState = "closed";
      currentQR = null;
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
      console.log(`Conexion cerrada (${statusCode}). Reconectando: ${shouldReconnect}`);
      if (shouldReconnect) {
        setTimeout(startWhatsApp, 3000);
      } else {
        console.log("Sesion cerrada (Logged Out). Limpiando credenciales y generando nuevo QR...");
        try {
          fs.rmSync(AUTH_FOLDER, { recursive: true, force: true });
        } catch (e) {
          console.error("Error al limpiar authFolder:", e);
        }
        setTimeout(startWhatsApp, 2000);
      }
    } else if (connection === "open") {
      connectionState = "open";
      currentQR = null;
      console.log("\n WhatsApp conectado exitosamente!");
      console.log(` Usuario conectado: ${sock.user?.id} (${sock.user?.name || "Sin nombre"})`);
      console.log(` Sebax listo para atender y prospectar 24/7.\n`);
    }
  });

  sock.ev.on("messages.upsert", async (m) => {
    if (!m.messages || !m.messages.length) return;
    console.log(`[messages.upsert] Evento recibido. Type: ${m.type}, Mensajes: ${m.messages.length}`);

    for (const msg of m.messages) {
      try {
        if (!msg?.message) continue;

        const remoteJid = msg.key.remoteJid;
        if (!remoteJid) continue;
        let recipientJid;
        try {
          recipientJid = await getMessageRecipientJid(msg);
        } catch (err) {
          console.error(`No se pudo resolver el destinatario para ${remoteJid}:`, err.message);
          continue;
        }

        if (remoteJid.includes("broadcast") || remoteJid.includes("@newsletter") || remoteJid.endsWith("@g.us")) {
          continue;
        }

        if (msg.key.id && botSentMessageIds.has(msg.key.id)) {
          botSentMessageIds.delete(msg.key.id);
          continue;
        }

        const isSelf = isSelfUser(remoteJid) || isSelfUser(recipientJid);
        if (msg.key.fromMe && !isSelf) continue;

        const mObj =
          msg.message?.ephemeralMessage?.message ||
          msg.message?.viewOnceMessage?.message ||
          msg.message?.viewOnceMessageV2?.message ||
          msg.message?.documentWithCaptionMessage?.message ||
          msg.message;

        const incomingText = (
          mObj?.conversation ||
          mObj?.extendedTextMessage?.text ||
          mObj?.imageMessage?.caption ||
          mObj?.videoMessage?.caption ||
          ""
        ).trim();
        if (!incomingText) continue;

        const messageKey = `${remoteJid}:${msg.key.id || incomingText}`;
        if (processedIncomingMessageIds.has(messageKey)) continue;
        processedIncomingMessageIds.add(messageKey);
        if (processedIncomingMessageIds.size > 500) {
          const [first] = processedIncomingMessageIds;
          processedIncomingMessageIds.delete(first);
        }

        console.log(`[Mensaje Entrante de ${remoteJid}] (respuesta a ${recipientJid}, isSelf: ${isSelf}) -> "${incomingText}"`);

        let replyText = getDiagnosticReply(incomingText);

        if (replyText) {
          console.log(`[Respuesta de diagnóstico sin herramientas para ${recipientJid}]`);
        } else if (isSelf) {
          try {
            const data = await callFastAPI("/webhook/whatsapp", {
              sender: "self_user",
              message: incomingText
            });
            replyText = data?.reply || "";
          } catch (err) {
            console.error("Error al conectar con agente Python para chat personal:", err.message);
          }
        } else {
          let leadReplied = false;
          try {
            const data = await callFastAPI("/api/leads/incoming", { sender: recipientJid, message: incomingText });
            if (data && data.is_lead && data.reply) {
              replyText = data.reply;
              leadReplied = true;
            }
          } catch (err) {
            console.error("Error al procesar mensaje de prospecto:", err.message);
          }

          if (!leadReplied) {
            try {
              const data = await callFastAPI("/webhook/whatsapp", { sender: recipientJid, message: incomingText });
              replyText = data?.reply || "";
            } catch (err) {
              console.error("Error al obtener respuesta de Sebax para", recipientJid, err.message);
            }
          }
        }

        if (replyText) {
          console.log(`[Enviando respuesta a ${recipientJid}] -> "${replyText.slice(0, 60)}..."`);
          const sent = await sock.sendMessage(recipientJid, { text: replyText });
          if (sent?.key?.id) {
            botSentMessageIds.add(sent.key.id);
            if (botSentMessageIds.size > 500) {
              const [first] = botSentMessageIds;
              botSentMessageIds.delete(first);
            }
          }
          console.log(`[WhatsApp acepto la respuesta para ${recipientJid}]`);
        }
      } catch (err) {
        console.error("Error al procesar mensaje individual de messages.upsert:", err);
      }
    }
  });

  sock.ev.on("messages.update", (updates) => {
    for (const { key, update } of updates) {
      if (key?.id && update?.status !== undefined) {
        const status = Number(update.status);
        messageStatusById.set(key.id, status);
        while (messageStatusById.size > 500) {
          messageStatusById.delete(messageStatusById.keys().next().value);
        }
        console.log(`[Acuse WhatsApp] id: ${key.id}, chat: ${key.remoteJid || "desconocido"}, status: ${getDeliveryStatusName(status)}`);
        if ((status === 0 || status >= 3) && deliveryStatusWaiters.has(key.id)) {
          deliveryStatusWaiters.get(key.id)(status);
        }
      }
    }
  });
}

app.listen(PORT, () => {
  console.log(` Servidor WhatsApp Bridge iniciado en http://localhost:${PORT}`);
  startWhatsApp();
});
