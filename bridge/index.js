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
      <html>
      <head><title>WhatsApp Agent Conectado</title><meta charset="utf-8">
      <style>
        body { font-family: system-ui, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #0f172a; color: #f8fafc; }
        .card { text-align: center; padding: 2rem; background: #1e293b; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.4); }
        .badge { display: inline-block; padding: 6px 16px; border-radius: 20px; background: #22c55e; color: #fff; font-weight: bold; margin-bottom: 1rem; }
      </style>
      </head>
      <body>
        <div class="card">
          <div class="badge">CONECTADO</div>
          <h2>Tu agente de WhatsApp está activo</h2>
          <p>Ya puedes enviarle mensajes desde tu cuenta de WhatsApp.</p>
        </div>
      </body>
      </html>
    `);
  }

  if (!currentQR) {
    return res.send(`
      <!DOCTYPE html>
      <html>
      <head><meta http-equiv="refresh" content="3"><title>Iniciando...</title><meta charset="utf-8">
      <style>body { font-family: system-ui, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; background: #0f172a; color: #94a3b8; }</style>
      </head>
      <body>
        <h3>Iniciando sesión y generando código QR...</h3>
      </body>
      </html>
    `);
  }

  try {
    const qrDataUrl = await QRCode.toDataURL(currentQR, { width: 340, margin: 2 });
    res.send(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>Escanear WhatsApp QR - Agente</title>
        <meta charset="utf-8">
        <meta http-equiv="refresh" content="20">
        <style>
          body { font-family: system-ui, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #0f172a; color: #f8fafc; }
          .card { text-align: center; padding: 2.5rem; background: #1e293b; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); max-width: 420px; }
          img { border-radius: 12px; border: 4px solid #38bdf8; margin: 1.5rem 0; }
          ol { text-align: left; font-size: 0.95rem; color: #cbd5e1; line-height: 1.6; }
        </style>
      </head>
      <body>
        <div class="card">
          <h2 style="margin-top:0;">Vincular WhatsApp</h2>
          <img src="${qrDataUrl}" alt="QR Code">
          <ol>
            <li>Abre WhatsApp en tu teléfono</li>
            <li>Toca <b>Menú</b> o <b>Configuración</b> &gt; <b>Dispositivos vinculados</b></li>
            <li>Toca <b>Vincular un dispositivo</b> y apunta la cámara a este código</li>
          </ol>
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
      console.log("\n📲 CÓDIGO QR GENERADO: http://localhost:" + PORT + "/qr\n");
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
      console.log("\n✅ ¡WhatsApp conectado exitosamente!");
      console.log(`👤 Usuario conectado: ${sock.user?.id} (${sock.user?.name || "Sin nombre"})`);
      console.log(`🤖 El agente está listo exclusivamente en tu chat personal.\n`);
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
                console.log(`📤 [Sebax respondió automáticamente al prospecto ${remoteJid}] -> "${data.reply}"`);
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

      console.log(`📩 [Chat Personal (Tú) | ${remoteJid}] -> "${text}"`);

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
        console.log(`📤 ¡Respuesta enviada con éxito a tu WhatsApp!`);
      }
    } catch (err) {
      console.error("Error al procesar mensaje entrante:", err);
    }
  });
}

app.listen(PORT, () => {
  console.log(`🌐 Servidor WhatsApp Bridge iniciado en http://localhost:${PORT}`);
  startWhatsApp();
});
