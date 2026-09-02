# Deploy no Render

Este projeto roda o Node (WhatsApp/Baileys) e o Python (Shopee) no mesmo container.

## Correção principal

O `server.js` é o único processo que abre a porta `PORT` do Render.
O `main.py` agora usa automaticamente `http://127.0.0.1:$PORT/send` quando `WHATSAPP_SERVICE_URL` não está definida.

**Não crie `WHATSAPP_SERVICE_URL=http://localhost:3333` no Render.**

## Variáveis

Preencha no Render as variáveis marcadas como `sync: false` no `render.yaml`, principalmente:

- `SHOPEE_APP_ID`
- `SHOPEE_SECRET`
- `SHOPEE_AFFILIATE_ID`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `WHATSAPP_GROUP_ID`

As demais já têm valores padrão no `render.yaml`.

## Supabase Storage

O Node restaura/salva a sessão do WhatsApp no bucket configurado por:

- `SUPABASE_STORAGE_BUCKET=whatsapp-session`
- `SUPABASE_SESSION_OBJECT=auth_info_baileys.backup.gz`

O diretório local padrão no Render é `/var/data/auth_info_baileys`.

## QR Code

Depois do deploy, abra a URL pública do serviço + `/qr` se for necessário escanear um novo QR Code.

Status: `/status`

## Importante sobre segredos

Não coloque `.env`, `auth_info_baileys/` ou `node_modules/` no GitHub. Use as Environment Variables do Render. Se as chaves que estavam no ZIP original já foram expostas, gere novas chaves/segredos antes de colocar o projeto em produção.
