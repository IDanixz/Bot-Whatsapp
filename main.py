import os
import sys
import json
import time
import hashlib
import re
import unicodedata
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# ============================================================
# CONFIGURAÇÕES
# ============================================================

SHOPEE_APP_ID = os.getenv("SHOPEE_APP_ID")
SHOPEE_SECRET = os.getenv("SHOPEE_SECRET")
SHOPEE_AFFILIATE_ID = os.getenv("SHOPEE_AFFILIATE_ID")
SHOPEE_API_URL = os.getenv(
    "SHOPEE_API_URL",
    "https://open-api.affiliate.shopee.com.br/graphql"
)

WHATSAPP_ENABLED = os.getenv("WHATSAPP_ENABLED", "false").lower() == "true"
WHATSAPP_CHANNEL_NAME = os.getenv("WHATSAPP_CHANNEL_NAME", "Divulga Promos")
WHATSAPP_CHANNEL_LINK = os.getenv("WHATSAPP_CHANNEL_LINK", "")

RENDER_PORT = os.getenv("PORT", "3333")

WHATSAPP_SERVICE_URL = os.getenv(
    "WHATSAPP_SERVICE_URL",
    f"http://127.0.0.1:{RENDER_PORT}"
).rstrip("/")

WHATSAPP_GROUP_ID = os.getenv("WHATSAPP_GROUP_ID", "")

SHOPEE_SEARCH_KEYWORD = os.getenv(
    "SHOPEE_SEARCH_KEYWORD",
    ""
)

SHOPEE_PRODUCT_LIMIT = int(
    os.getenv("SHOPEE_PRODUCT_LIMIT", "5")
)

POST_INTERVAL_SEGUNDOS = int(
    os.getenv("POST_INTERVAL_SEGUNDOS", "30")
)

MIN_VENDAS = int(
    os.getenv("MIN_VENDAS", "1000")
)

MIN_AVALIACAO = float(
    os.getenv("MIN_AVALIACAO", "4.5")
)

SHOPEE_BUSCA_BRUTA = int(
    os.getenv("SHOPEE_BUSCA_BRUTA", "50")
)

INTERVALO_PAGINAS = float(
    os.getenv("INTERVALO_PAGINAS", "0.3")
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

TERMOS_BLOQUEADOS_FEMININOS = [
    termo.strip()
    for termo in os.getenv(
        "TERMOS_BLOQUEADOS_FEMININOS",
        ""
    ).split(",")
    if termo.strip()
]

# ============================================================
# TERMOS EXTRAS PARA FILTRO FEMININO
# ============================================================

TERMOS_ROUPA_FEMININA = [
    "roupa",
    "roupas",
    "moda",
    "conjunto",
    "conjuntos",
    "fitness",
    "academia",
    "praia",
    "banho",
    "biquini",
    "bikini",
    "maio",
    "maiô",
    "top",
    "cropped",
    "legging",
    "vestido",
    "vestidos",
    "saia",
    "saias",
    "short",
    "shorts",
    "body",
    "lingerie",
    "sutia",
    "sutiã",
    "calcinha",
    "camisola",
    "macacao",
    "macacão",
    "blusa",
    "camisa",
    "camiseta",
    "regata",
    "calca",
    "calça",
    "jeans",
    "praia",
    "banho"
]

# ============================================================
# SUPABASE
# ============================================================

supabase: Client = None
postados_cache = set()


# ============================================================
# NORMALIZA TEXTO
# ============================================================

def normalizar_texto(texto):
    if not texto:
        return ""

    texto = str(texto).lower()

    texto = unicodedata.normalize(
        "NFD",
        texto
    )

    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )

    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


# ============================================================
# CONFIGURAÇÃO
# ============================================================

def checar_configuracao():

    global supabase

    erros = []

    if not SHOPEE_APP_ID:
        erros.append("SHOPEE_APP_ID")

    if not SHOPEE_SECRET:
        erros.append("SHOPEE_SECRET")

    if not SUPABASE_URL:
        erros.append("SUPABASE_URL")

    if not SUPABASE_KEY:
        erros.append("SUPABASE_KEY")

    if WHATSAPP_ENABLED and not WHATSAPP_GROUP_ID:
        erros.append("WHATSAPP_GROUP_ID")

    if erros:
        print(
            "❌ Variáveis ausentes:",
            ", ".join(erros)
        )
        sys.exit(1)

    supabase = create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )


# ============================================================
# HISTÓRICO
# ============================================================

def carregar_historico_supabase():

    global postados_cache

    postados_cache = set()

    try:

        inicio = 0

        while True:

            fim = inicio + 999

            resposta = (
                supabase
                .table("produtos_postados")
                .select("produto_id")
                .range(inicio, fim)
                .execute()
            )

            dados = resposta.data or []

            for item in dados:

                produto_id = item.get("produto_id")

                if produto_id:
                    postados_cache.add(
                        str(produto_id)
                    )

            if len(dados) < 1000:
                break

            inicio += 1000

        print(
            f"📚 Histórico carregado: {len(postados_cache)} produtos"
        )

    except Exception as e:

        print(
            "⚠️ Erro ao carregar histórico:",
            e
        )


def produto_ja_postado(produto_id):

    return str(produto_id) in postados_cache


def salvar_produto_postado(produto_id, link):

    try:

        supabase.table(
            "produtos_postados"
        ).insert({
            "produto_id": str(produto_id),
            "link": link
        }).execute()

        postados_cache.add(
            str(produto_id)
        )

        return True

    except Exception as e:

        texto = str(e).lower()

        if (
            "duplicate" in texto
            or "unique" in texto
            or "23505" in texto
        ):
            postados_cache.add(
                str(produto_id)
            )

            return True

        print(
            "⚠️ Erro ao salvar histórico:",
            e
        )

        return False


# ============================================================
# FILTRO FEMININO
# ============================================================

def produto_feminino(nome):

    texto = normalizar_texto(nome)

    # --------------------------------------------------------
    # 1. Termos colocados diretamente no .env
    # --------------------------------------------------------

    for termo in TERMOS_BLOQUEADOS_FEMININOS:

        termo_normalizado = normalizar_texto(termo)

        if (
            termo_normalizado
            and termo_normalizado in texto
        ):
            return True

    # --------------------------------------------------------
    # 2. Filtro inteligente:
    #
    # feminino/feminina + qualquer termo de roupa
    # --------------------------------------------------------

    feminino = (
        "feminino" in texto
        or "feminina" in texto
    )

    if feminino:

        for termo in TERMOS_ROUPA_FEMININA:

            termo_normalizado = normalizar_texto(
                termo
            )

            if termo_normalizado in texto:
                return True

    # --------------------------------------------------------
    # 3. Combinações específicas que costumam escapar
    # --------------------------------------------------------

    combinacoes = [

        "conjunto feminino",
        "conjuntos feminino",
        "conjunto feminina",
        "conjuntos feminina",

        "roupa feminino",
        "roupa feminina",
        "roupas feminina",
        "roupas femininas",

        "moda feminino",
        "moda feminina",

        "fitness feminino",
        "fitness feminina",

        "academia feminino",
        "academia feminina",

        "praia feminino",
        "praia feminina",

        "banho feminino",
        "banho feminina",

        "top feminino",
        "top feminina",

        "short feminino",
        "shorts feminino",

        "legging feminino",
        "legging feminina",

        "calca feminino",
        "calca feminina",

        "vestido feminino",
        "vestido feminina"
    ]

    for combinacao in combinacoes:

        if normalizar_texto(combinacao) in texto:
            return True

    return False


# ============================================================
# FILTRO PRINCIPAL
# ============================================================

def produto_passou_filtro(produto):

    nome = produto.get(
        "productName",
        ""
    )

    vendas = int(
        produto.get("sales", 0) or 0
    )

    avaliacao = float(
        produto.get("rating", 0) or 0
    )

    # --------------------------------------------------------
    # BLOQUEIO FEMININO
    # --------------------------------------------------------

    if produto_feminino(nome):

        return False

    # --------------------------------------------------------
    # VENDAS
    # --------------------------------------------------------

    if vendas < MIN_VENDAS:

        return False

    # --------------------------------------------------------
    # AVALIAÇÃO
    # --------------------------------------------------------

    if avaliacao < MIN_AVALIACAO:

        return False

    return True


# ============================================================
# ASSINATURA SHOPEE
# ============================================================

def gerar_assinatura(payload):

    timestamp = int(time.time())

    body = json.dumps(
        payload,
        separators=(",", ":"),
        ensure_ascii=False
    )

    assinatura = hashlib.sha256(
        (
            SHOPEE_APP_ID
            + str(timestamp)
            + body
            + SHOPEE_SECRET
        ).encode()
    ).hexdigest()

    return timestamp, assinatura


# ============================================================
# BUSCA SHOPEE
# ============================================================

def buscar_produtos(keyword, page):

    query = """
    query {
        productOfferV2(
            keyword: "%s",
            limit: %s,
            page: %s
        ) {
            nodes {
                itemId
                productName
                priceMin
                priceMax
                discount
                sales
                rating
                offerLink
                imageUrl
            }
        }
    }
    """ % (
        keyword.replace('"', '\\"'),
        SHOPEE_BUSCA_BRUTA,
        page
    )

    payload = {
        "query": query
    }

    timestamp, assinatura = gerar_assinatura(
        payload
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={SHOPEE_APP_ID}, Timestamp={timestamp}, Signature={assinatura}"
    }

    resposta = requests.post(
        SHOPEE_API_URL,
        headers=headers,
        json=payload,
        timeout=30
    )

    resposta.raise_for_status()

    dados = resposta.json()

    return (
        dados
        .get("data", {})
        .get("productOfferV2", {})
        .get("nodes", [])
    )


# ============================================================
# FORMATA PRODUTO
# ============================================================

def formatar_produto(produto):

    nome = produto.get(
        "productName",
        "Produto"
    )

    preco_min = float(
        produto.get("priceMin", 0) or 0
    )

    preco_max = float(
        produto.get("priceMax", 0) or 0
    )

    desconto = float(
        produto.get("discount", 0) or 0
    )

    link = produto.get(
        "offerLink",
        ""
    )

    if preco_max > preco_min:
        preco_original = preco_max
    else:
        preco_original = 0

    if desconto > 0:

        preco_atual = (
            preco_original
            * (1 - desconto / 100)
        )

    else:

        preco_atual = preco_min

    mensagem = f"""🔥 *{nome}*

"""

    if preco_original > preco_atual:

        mensagem += (
            f"~R$ {preco_original:.2f}~ "
            f"🏷️ -{desconto:.0f}% OFF\n"
        )

    mensagem += (
        f"💵 *R$ {preco_atual:.2f}*\n\n"
        f"🔗 {link}\n\n"
        f"{WHATSAPP_CHANNEL_NAME}\n"
        f"{WHATSAPP_CHANNEL_LINK}\n\n"
        f"#Anuncio #DivulgaPromos"
    )

    return mensagem


# ============================================================
# ENVIA WHATSAPP
# ============================================================

def enviar_whatsapp(mensagem, imagem_url):

    if not WHATSAPP_ENABLED:
        return False

    payload = {
        "group_id": WHATSAPP_GROUP_ID,
        "message": mensagem,
        "image_url": imagem_url
    }

    resposta = requests.post(
        f"{WHATSAPP_SERVICE_URL}/send",
        json=payload,
        timeout=60
    )

    resposta.raise_for_status()

    return True


# ============================================================
# PROCESSA PRODUTO
# ============================================================

def processar_produto(produto):

    try:

        produto_id = produto.get(
            "itemId"
        )

        nome = produto.get(
            "productName",
            ""
        )

        if not produto_id:
            return False

        if produto_ja_postado(produto_id):
            return False

        if not produto_passou_filtro(produto):
            return False

        mensagem = formatar_produto(
            produto
        )

        imagem_url = produto.get(
            "imageUrl",
            ""
        )

        print(
            f"🔥 Postando: {nome}"
        )

        enviar_whatsapp(
            mensagem,
            imagem_url
        )

        salvar_produto_postado(
            produto_id,
            produto.get("offerLink", "")
        )

        print(
            "✅ Produto enviado"
        )

        return True

    except Exception as e:

        print(
            f"⚠️ Erro no produto: {e}"
        )

        return False


# ============================================================
# UMA RODADA
# ============================================================

def rodar_uma_vez():

    enviados = 0
    pagina = 1

    while enviados < SHOPEE_PRODUCT_LIMIT:

        try:

            produtos = buscar_produtos(
                SHOPEE_SEARCH_KEYWORD,
                pagina
            )

        except Exception as e:

            print(
                f"⚠️ Erro na página {pagina}: {e}"
            )

            break

        if not produtos:
            break

        for produto in produtos:

            if enviados >= SHOPEE_PRODUCT_LIMIT:
                break

            sucesso = processar_produto(
                produto
            )

            if sucesso:

                enviados += 1

                # INTERVALO GLOBAL ENTRE POSTS
                if (
                    enviados
                    < SHOPEE_PRODUCT_LIMIT
                ):
                    print(
                        f"⏳ Aguardando {POST_INTERVAL_SEGUNDOS}s..."
                    )

                    time.sleep(
                        POST_INTERVAL_SEGUNDOS
                    )

        pagina += 1

        time.sleep(
            INTERVALO_PAGINAS
        )

    print(
        f"🏁 Rodada finalizada: {enviados} enviados"
    )


# ============================================================
# LOOP
# ============================================================

def rodar_continuamente():

    while True:

        try:

            rodar_uma_vez()

        except Exception as e:

            print(
                "⚠️ Erro na rodada:",
                e
            )

        print(
            "🔄 Nova rodada..."
        )

        time.sleep(
            POST_INTERVAL_SEGUNDOS
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    checar_configuracao()

    carregar_historico_supabase()

    rodar_continuamente()
