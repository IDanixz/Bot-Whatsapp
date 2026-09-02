# DivulgaPromos — Shopee → WhatsApp

Este projeto busca promoções pela API da Shopee, filtra os produtos e envia somente para o WhatsApp.

## Como iniciar

1. Copie `.env.example` para `.env` e preencha suas credenciais.
2. No terminal 1: `npm install` e depois `npm start`.
3. No terminal 2: `python -m pip install -r requirements.txt` e depois `python main.py --loop`.

O WhatsApp precisa estar conectado e o `WHATSAPP_GROUP_ID` configurado.


## Fotos no WhatsApp
As promoções agora enviam `imageUrl` retornada pela API da Shopee como foto, com a mensagem da promoção na legenda. Se a Shopee não retornar imagem para um produto, a mensagem será enviada apenas como texto.

## Render

O projeto inclui `Dockerfile`, `render.yaml` e `CONFIGURAR_NO_RENDER.md`.
O Node é o único processo que escuta a porta `$PORT` do Render; o Python chama o Node localmente pela mesma porta. Não configure `WHATSAPP_SERVICE_URL` com `localhost:3333` no Render.
