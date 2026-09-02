const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason
} = require("@whiskeysockets/baileys");

const express = require("express");
const qrcode = require("qrcode-terminal");
const pino = require("pino");

const logger = pino({ level: "silent" });

// Pasta onde a sessão do WhatsApp fica salva (a mesma que você já usou
// para escanear o QR code). Não apague essa pasta — é ela que evita
// pedir o QR de novo a cada execução.
const AUTH_FOLDER = process.env.WHATSAPP_AUTH_FOLDER || "auth_info_baileys";
const PORT = process.env.PORT || 3333;

let sock = null;
let conectado = false;

// ===================== CONEXÃO COM O WHATSAPP =====================

async function conectar() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_FOLDER);

  sock = makeWASocket({
    auth: state,
    logger,
    markOnlineOnConnect: false
  });

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.log("\n📱 ESCANEIE O QR CODE NO WHATSAPP:\n");
      qrcode.generate(qr, { small: true });
    }

    if (connection === "open") {
      conectado = true;
      console.log("\n✅ WHATSAPP CONECTADO! Serviço pronto para receber pedidos de envio.");
    }

    if (connection === "close") {
      conectado = false;
      const codigo = lastDisconnect?.error?.output?.statusCode;

      if (codigo !== DisconnectReason.loggedOut) {
        console.log("\n⚠️ Conexão caiu. Reconectando em 3s...");
        setTimeout(conectar, 3000);
      } else {
        console.log(
          "\n❌ WhatsApp deslogado. Apague a pasta de sessão " +
          `("${AUTH_FOLDER}") e rode de novo para escanear um novo QR code.`
        );
      }
    }
  });
}

// ===================== API HTTP =====================

const app = express();
app.use(express.json());

// Healthcheck simples — útil para saber se o serviço está de pé e conectado.
app.get("/status", (req, res) => {
  res.json({ conectado });
});

// Lista os grupos disponíveis, com o ID de cada um.
// Use isso uma vez para descobrir o group_id que vai no .env do bot Python.
app.get("/grupos", async (req, res) => {
  if (!conectado || !sock) {
    return res.status(503).json({ erro: "WhatsApp não está conectado ainda." });
  }

  try {
    const grupos = await sock.groupFetchAllParticipating();

    const lista = Object.entries(grupos).map(([id, grupo]) => ({
      id,
      nome: grupo.subject
    }));

    res.json({ grupos: lista });
  } catch (erro) {
    console.log("\n❌ Erro ao listar grupos:", erro);
    res.status(500).json({ erro: "Falha ao listar grupos." });
  }
});

// Endpoint principal: recebe { group_id, message } e envia via Baileys.
app.post("/send", async (req, res) => {
  const { group_id, message, image_url } = req.body || {};

  if (!group_id || !message) {
    return res.status(400).json({
      erro: "Campos obrigatórios: group_id e message."
    });
  }

  if (!conectado || !sock) {
    return res.status(503).json({ erro: "WhatsApp não está conectado ainda." });
  }

  try {
    if (image_url) {
      await sock.sendMessage(group_id, {
        image: { url: image_url },
        caption: message
      });
    } else {
      await sock.sendMessage(group_id, { text: message });
    }

    const preview = message.length > 80 ? message.slice(0, 80) + "..." : message;
    console.log(`\n🎉 MENSAGEM ENVIADA`);
    console.log(`📱 Grupo: ${group_id}`);
    console.log(`📝 Conteúdo: ${preview}`);
    console.log(`🖼️ Foto: ${image_url ? "enviada" : "não enviada"}`);

    res.json({ ok: true });
  } catch (erro) {
    console.log("\n❌ ERRO ao enviar mensagem:", erro);
    res.status(500).json({
      erro: "Falha ao enviar mensagem.",
      detalhe: String(erro)
    });
  }
});

app.listen(PORT, () => {
  console.log(`🚀 API do WhatsApp rodando em http://localhost:${PORT}`);
  console.log(`   POST http://localhost:${PORT}/send   { group_id, message }`);
  console.log(`   GET  http://localhost:${PORT}/grupos`);
  console.log(`   GET  http://localhost:${PORT}/status`);
});

console.log("🚀 Iniciando serviço WhatsApp...");
console.log("⏳ Conectando ao WhatsApp...");

conectar();
