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

function isSelfUser(jid) {
  if (!jid || !sock || !sock.user) return false;
  try {
    if (areJidsSameUser(jid, sock.user.id)) return true;
    if (sock.user.lid && areJidsSameUser(jid, sock.user.lid)) return true;
  } catch (e) {}

  // Comparación por número de teléfono
  const d1 = jid.split("@")[0].replace(/\D/g, "");
  const d2 = (sock.user.id || "").split("@")[0].replace(/\D/g, "");
  if (d1.length >= 8 && d2.length >= 8) {
    if (d1.endsWith(d2.slice(-8)) || d2.endsWith(d1.slice(-8))) {
      return true;
    }
  }
  return false;
}

app.get("/qr", async (req, res) => {
  if (connectionState === "open") {
    return res.send(`
      <!DOCTYPE html>
      <html lang="es">
      <head>
        <title>WhatsApp Conectado | SSSSolutions</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
          * { box-sizing: border-box; margin: 0; padding: 0; }
          body {
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
            display: flex; align-items: center; justify-content: center;
            min-height: 100vh; background: #f8fafc; color: #09090b; padding: 20px;
          }
          .card {
            text-align: center; padding: 2.5rem 2rem; background: #ffffff;
            border-radius: 28px; border: 1px solid rgba(0,0,0,0.07);
            box-shadow: 0 20px 50px rgba(0,0,0,0.04); max-width: 420px; width: 100%;
          }
          .badge {
            display: inline-flex; align-items: center; gap: 6px;
            padding: 6px 16px; border-radius: 20px;
            background: #ecfdf5; color: #059669; font-weight: 700; font-size: 0.8rem;
            text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 1.2rem;
          }
          .dot { width: 8px; height: 8px; border-radius: 50%; background: #10b981; }
          h2 { font-size: 1.25rem; font-weight: 800; letter-spacing: -0.4px; margin-bottom: 0.5rem; }
          p { font-size: 0.88rem; color: #71717a; line-height: 1.5; }
          .agency { margin-top: 1.5rem; font-size: 0.74rem; font-weight: 600; color: #a1a1aa; }
        </style>
      </head>
      <body>
        <div class="card">
          <div class="badge"><span class="dot"></span> CONECTADO</div>
          <h2>WhatsApp Vinculado con Éxito</h2>
          <p>Sebax está en línea y operando de forma continua las 24 horas.</p>
          <div class="agency">SSSSolutions • @ssss.olutions</div>
        </div>
      </body>
      </html>
    `);
  }

  if (!currentQR) {
    return res.send(`
      <!DOCTYPE html>
      <html lang="es">
      <head>
        <meta http-equiv="refresh" content="3">
        <title>Iniciando Sebax WhatsApp...</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;700&display=swap" rel="stylesheet">
        <style>
          body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            display: flex; align-items: center; justify-content: center;
            min-height: 100vh; background: #f8fafc; color: #71717a; margin: 0;
          }
          .box { text-align: center; }
          .spinner { width: 32px; height: 32px; border: 3px solid rgba(0,0,0,0.1); border-top-color: #09090b; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 1rem auto; }
          @keyframes spin { to { transform: rotate(360deg); } }
        </style>
      </head>
      <body>
        <div class="box">
          <div class="spinner"></div>
          <p style="font-size:0.9rem; font-weight:600; color:#09090b;">Generando código QR seguro...</p>
        </div>
      </body>
      </html>
    `);
  }

  try {
    const qrDataUrl = await QRCode.toDataURL(currentQR, { width: 320, margin: 2 });
    res.send(`
      <!DOCTYPE html>
      <html lang="es">
      <head>
        <title>Vincular WhatsApp | SSSSolutions</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="25">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
          * { box-sizing: border-box; margin: 0; padding: 0; }
          body {
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
            display: flex; align-items: center; justify-content: center;
            min-height: 100vh; background: #f8fafc; color: #09090b; padding: 20px;
          }
          .card {
            text-align: center; padding: 2.2rem 1.8rem; background: #ffffff;
            border-radius: 28px; border: 1px solid rgba(0,0,0,0.07);
            box-shadow: 0 20px 50px rgba(0,0,0,0.04); max-width: 400px; width: 100%;
          }
          .brand {
            font-size: 0.76rem; font-weight: 700; text-transform: uppercase;
            letter-spacing: 1px; color: #71717a; margin-bottom: 0.4rem;
          }
          h2 { font-size: 1.3rem; font-weight: 800; letter-spacing: -0.4px; margin-bottom: 0.3rem; color: #09090b; }
          p.subtitle { font-size: 0.8rem; color: #71717a; margin-bottom: 1.2rem; }
          .qr-wrapper {
            background: #ffffff; padding: 12px; border-radius: 20px;
            display: inline-block; border: 1px solid rgba(0,0,0,0.08);
            box-shadow: 0 8px 24px rgba(0,0,0,0.04); margin-bottom: 1.2rem;
          }
          .qr-wrapper img { display: block; border-radius: 12px; max-width: 100%; height: auto; }
          .steps {
            text-align: left; background: #f8fafc; border-radius: 16px;
            padding: 14px 16px; font-size: 0.78rem; color: #3f3f46; line-height: 1.5;
            border: 1px solid rgba(0,0,0,0.04);
          }
          .steps ol { padding-left: 18px; margin: 0; }
          .steps li { margin-bottom: 4px; }
          .steps li:last-child { margin-bottom: 0; }
        </style>
      </head>
      <body>
        <div class="card">
          <div class="brand">SSSSolutions</div>
          <h2>Vincular WhatsApp</h2>
          <p class="subtitle">Escanea este código para activar a Sebax 24/7</p>
          <div class="qr-wrapper">
            <img src="${qrDataUrl}" alt="Código QR WhatsApp">
          </div>
          <div class="steps">
            <ol>
              <li>Abre <b>WhatsApp</b> en tu celular</li>
              <li>Toca <b>Ajustes</b> &gt; <b>Dispositivos vinculados</b></li>
              <li>Toca <b>Vincular un dispositivo</b> y apunta la cámara</li>
            </ol>
          </div>
        </div>
      </body>
      </html>
    `);
  } catch (err) {
    res.status(500).send("Error generando QR: " + err.message);
  }
});

app.get("/status", (req, res) => {
  res.json({
    status: connectionState,
    has_qr: !!currentQR,
    user: sock?.user ? { id: sock.user.id, name: sock.user.name } : null
  });
});

// Endpoint para que el Agente 3D pueda enviar mensajes de WhatsApp de forma autónoma
app.post("/send", async (req, res) => {
  const { to, text } = req.body;
  if (!sock || connectionState !== "open") {
    return res.status(503).json({ error: "WhatsApp no está conectado actualmente." });
  }
  if (!text) {
    return res.status(400).json({ error: "El texto del mensaje no puede estar vacío." });
  }
  try {
    let jid = to || sock.user.id;
    if (!jid.includes("@")) {
      const cleanDigits = jid.replace(/\D/g, "");
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
    browser: ["Agente Personal", "Chrome", "1.0.0"]
  });

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      currentQR = qr;
      connectionState = "qr_ready";
      console.log("\n CÓDIGO QR GENERADO: http://localhost:" + PORT + "/qr\n");
      qrcodeTerminal.generate(qr, { small: true });
    }

    if (connection === "close") {
      connectionState = "closed";
      currentQR = null;
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
      console.log(`Conexión cerrada (${statusCode}). Reconectando: ${shouldReconnect}`);
      if (shouldReconnect) {
        setTimeout(startWhatsApp, 4000);
      } else {
        console.log("Sesión cerrada (Logged Out). Limpiando credenciales y generando nuevo QR...");
        try {
          fs.rmSync(authFolder, { recursive: true, force: true });
        } catch (e) {
          console.error("Error al limpiar authFolder:", e);
        }
        setTimeout(startWhatsApp, 3000);
      }
    } else if (connection === "open") {
      connectionState = "open";
      currentQR = null;
      console.log("\n ¡WhatsApp conectado exitosamente!");
      console.log(` Usuario conectado: ${sock.user?.id} (${sock.user?.name || "Sin nombre"})`);
      console.log(` El agente está listo exclusivamente en tu chat personal.\n`);
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

      // Verificamos si es el chat personal de "Mensaje a ti mismo" (Tú)
      const isSelf = isSelfUser(remoteJid);

      // Si no es el chat personal de Sebastián, revisamos si es un prospecto de negocio respondiendo a una propuesta
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
                console.log(` [Sebax respondió automáticamente al prospecto ${remoteJid}] -> "${data.reply}"`);
              }
            }
          } catch (e) {
            console.error("Error al procesar mensaje de prospecto entrante:", e.message);
          }
        }
        return;
      }

      // Obtener el texto del mensaje
      const text =
        msg.message.conversation ||
        msg.message.extendedTextMessage?.text ||
        msg.message.imageMessage?.caption ||
        "";

      if (!text || text.trim() === "") return;

      console.log(` [Chat Personal (Tú) | ${remoteJid}] -> "${text}"`);

      // Enviar webhook al agente Python con timeout generoso de 90s
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
        // Enviar respuesta al chat personal
        const sent = await sock.sendMessage(remoteJid, { text: replyText });
        if (sent?.key?.id) {
          botSentMessageIds.add(sent.key.id);
          if (botSentMessageIds.size > 500) {
            const [first] = botSentMessageIds;
            botSentMessageIds.delete(first);
          }
        }
        console.log(` ¡Respuesta enviada con éxito a tu WhatsApp!`);
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
