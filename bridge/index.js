process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";

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

dotenv.config({ path: path.resolve(__dirname, "../.env") });

const PORT = process.env.BRIDGE_PORT || 3000;
const AGENT_WEBHOOK_URL = process.env.AGENT_WEBHOOK_URL || "http://127.0.0.1:8000/webhook/whatsapp";

const app = express();
app.use(express.json());

let currentQR = null;
let connectionState = "starting";
let sock = null;
const botSentMessageIds = new Set();

function normalizePhone(phone) {
  let clean = (phone || "").toString().replace(/\D/g, "");
  if (clean.length === 10) {
    clean = "521" + clean;
  } else if (clean.length === 12 && clean.startsWith("52") && !clean.startsWith("521")) {
    clean = "521" + clean.slice(2);
  }
  return clean;
}

function isSelfUser(jid) {
  if (!jid || !sock || !sock.user) return false;
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
    const { phone } = req.body;
    if (!phone) {
      return res.status(400).json({ error: "Ingresa tu número de teléfono." });
    }
    const clean = normalizePhone(phone);
    if (clean.length < 10) {
      return res.status(400).json({ error: "Número no válido. Debe incluir clave lada (ej. 8711234567 o 5218711234567)." });
    }
    if (!sock) {
      return res.status(503).json({ error: "El conector de WhatsApp está arrancando. Intenta en 5 segundos." });
    }
    if (connectionState === "open") {
      return res.json({ already_connected: true });
    }

    const rawCode = await sock.requestPairingCode(clean);
    const formattedCode = rawCode ? rawCode.match(/.{1,4}/g)?.join("-") || rawCode : "";
    res.json({ success: true, code: formattedCode });
  } catch (err) {
    console.error("Error al generar código de vinculación:", err.message);
    res.status(500).json({ error: err.message || "No se pudo generar el código. Verifica el número e intenta nuevamente." });
  }
});

app.post("/reset", async (req, res) => {
  try {
    const authFolder = path.resolve(__dirname, "auth_info_baileys");
    try {
      fs.rmSync(authFolder, { recursive: true, force: true });
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
                <input type="tel" id="phone" class="phone-input" placeholder="Ej: 8711234567 o 5218711234567" autocomplete="tel">
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
            document.getElementById('connectedUserText').textContent = 'Conectado a ' + user + '. Sebax esta operando 24/7.';
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
    let jid = to || sock.user.id;
    if (!jid.includes("@")) {
      const cleanDigits = normalizePhone(jid);
      jid = `${cleanDigits}@s.whatsapp.net`;
    }
    const sent = await sock.sendMessage(jid, { text });
    if (sent?.key?.id) {
      botSentMessageIds.add(sent.key.id);
    }
    res.json({ success: true, jid });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

async function startWhatsApp() {
  const authFolder = path.resolve(__dirname, "auth_info_baileys");
  const { state, saveCreds } = await useMultiFileAuthState(authFolder);
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
          fs.rmSync(authFolder, { recursive: true, force: true });
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
    try {
      const msg = m.messages[0];
      if (!msg || !msg.message) return;

      const remoteJid = msg.key.remoteJid;
      if (!remoteJid) return;

      // Descartar mensajes emitidos por el propio bot
      if (msg.key.id && botSentMessageIds.has(msg.key.id)) {
        botSentMessageIds.delete(msg.key.id);
        return;
      }

      const isSelf = isSelfUser(remoteJid);

      // Si es un prospecto respondiendo a una propuesta
      if (!isSelf) {
        if (remoteJid.endsWith("@g.us") || remoteJid.includes("@newsletter")) {
          return;
        }

        const incomingText =
          msg.message.conversation ||
          msg.message.extendedTextMessage?.text ||
          msg.message.imageMessage?.caption ||
          "";

        if (incomingText && incomingText.trim() !== "") {
          try {
            const resp = await fetch("http://127.0.0.1:8000/api/leads/incoming", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ sender: remoteJid, message: incomingText }),
              signal: AbortSignal.timeout(25000)
            });

            if (resp.ok) {
              const data = await resp.json();
              if (data.is_lead && data.reply) {
                const sent = await sock.sendMessage(remoteJid, { text: data.reply });
                if (sent?.key?.id) {
                  botSentMessageIds.add(sent.key.id);
                }
                console.log(` [Sebax respondio automaticamente al prospecto ${remoteJid}] -> "${data.reply}"`);
              }
            }
          } catch (e) {
            console.error("Error al procesar mensaje de prospecto entrante:", e.message);
          }
        }
        return;
      }

      // Chat personal de Sebastian
      const text =
        msg.message.conversation ||
        msg.message.extendedTextMessage?.text ||
        msg.message.imageMessage?.caption ||
        "";

      if (!text || text.trim() === "") return;

      console.log(` [Chat Personal (Tu) | ${remoteJid}] -> "${text}"`);

      let replyText = "";
      try {
        const response = await fetch(AGENT_WEBHOOK_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sender: "self_user",
            message: text
          }),
          signal: AbortSignal.timeout(90000)
        });

        if (response.ok) {
          const data = await response.json();
          replyText = data?.reply || "";
        } else {
          console.error(`Error HTTP ${response.status} desde Agente Python`);
        }
      } catch (err) {
        console.error("Error al conectar con agente Python:", err.message);
      }

      if (replyText) {
        const sent = await sock.sendMessage(remoteJid, { text: replyText });
        if (sent?.key?.id) {
          botSentMessageIds.add(sent.key.id);
          if (botSentMessageIds.size > 500) {
            const [first] = botSentMessageIds;
            botSentMessageIds.delete(first);
          }
        }
        console.log(` Respuesta enviada con exito a tu WhatsApp!`);
      }
    } catch (err) {
      console.error("Error al procesar mensaje entrante:", err);
    }
  });
}

app.listen(PORT, () => {
  console.log(` Servidor WhatsApp Bridge iniciado en http://localhost:${PORT}`);
  startWhatsApp();
});
