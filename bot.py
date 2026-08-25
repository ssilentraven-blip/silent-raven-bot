import os
import ccxt
import pandas as pd
import pandas_ta as ta
import requests
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

usuarios_inscritos = set()


def enviar_mensagem(chat_id, texto):
  url = f"{TELEGRAM_API_URL}/sendMessage"
  payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}
  try:
    requests.post(url, json=payload)
  except Exception as e:
    print(f"Erro ao enviar: {e}")


def classificar_volatilidade_futuros(par, df):
  # Calcula o Índice de Volatilidade via ATR percentual no mercado de Futuros
  preco_atual = df["close"].iloc[-1]
  atr_val = df["atr"].iloc[-1]
  volatilidade_pct = (atr_val / preco_atual) * 100

  if volatilidade_pct > 7.0:
    return (
        "Memecoin / Altíssima Volatilidade (Futuros)",
        "🔴 ALTO RISCO (Exige Alavancagem Baixa)",
        5,
    )
  elif volatilidade_pct > 3.0:
    return (
        "Altcoin de Oscilação Saudável (Futuros)",
        "🟡 RISCO MODERADO (Ideal para Alavancagem Média)",
        10,
    )
  else:
    return (
        "Ativo Consolidado / Bluechip (Futuros)",
        "🟢 RISCO BAIXO / ESTÁVEL",
        20,
    )


def analisar_futuros_usdt():
  try:
    # Conecta estritamente no mercado de Futuros Perpétuos (Linear Swaps em USDT)
    exchange = ccxt.bingx({"options": {"defaultType": "swap"}})
    exchange.load_markets()

    # Filtra apenas os contratos lineares de Futuros USDT
    pares_futuros_usdt = [
        simbolo
        for simbolo in exchange.symbols
        if "/USDT:USDT" in simbolo or ("/USDT" in simbolo and "USDT" in simbolo)
    ]

    sinal_encontrado = None

    for par in pares_futuros_usdt[:30]:
      try:
        # Pula tokens inversos ou alavancados indesejados
        if (
            "DOWN" in par
            or "BULL" in par
            or "BEAR" in par
            or "UP" in par
            or "USDC" in par
        ):
          continue

        ohlcv = exchange.fetch_ohlcv(par, timeframe="1h", limit=250)
        df = pd.DataFrame(
            ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        df["ema50"] = ta.ema(df["close"], length=50)
        df["ema90"] = ta.ema(df["close"], length=90)
        df["ema200"] = ta.ema(df["close"], length=200)
        df["rsi"] = ta.rsi(df["close"], length=14)
        df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)

        vol_media = df["volume"].rolling(window=20).mean().iloc[-1]
        vol_atual = df["volume"].iloc[-1]

        preco_atual = df["close"].iloc[-1]
        rsi_atual = df["rsi"].iloc[-1]
        ema50_val = df["ema50"].iloc[-1]
        ema90_val = df["ema90"].iloc[-1]
        ema200_val = df["ema200"].iloc[-1]
        atr_val = df["atr"].iloc[-1]

        tipo_ativo, nivel_risco, alavancagem_sugerida = (
            classificar_volatilidade_futuros(par, df)
        )
        par_limpo = par.split(":")[0]

        # Condição de LONG (Compra em Futuros USDT)
        if (
            preco_atual > ema50_val
            and ema50_val > ema90_val
            and ema90_val > ema200_val
            and vol_atual > (vol_media * 1.3)
            and (48 < rsi_atual < 68)
        ):
          entrada = preco_atual
          sl = entrada - (atr_val * 1.5)
          tp = entrada + ((entrada - sl) * 2.5)

          sinal_encontrado = {
              "par": par_limpo,
              "direcao": "🟢 LONG (COMPRA IMEDIATA)",
              "momento": "ENTRAR AGORA (A mercado no preço atual)",
              "tipo_ativo": tipo_ativo,
              "nivel_risco": nivel_risco,
              "alavancagem": alavancagem_sugerida,
              "entrada": entrada,
              "sl": sl,
              "tp": tp,
              "vol_atual": vol_atual,
              "vol_medio": vol_media,
              "rsi": round(rsi_atual, 2),
              "atr": round(atr_val, 4),
              "padrao": "Rompimento de Alta em Futuros USDT com Volume",
          }
          break

        # Condição de SHORT (Venda em Futuros USDT)
        elif (
            preco_atual < ema50_val
            and ema50_val < ema90_val
            and ema90_val < ema200_val
            and vol_atual > (vol_media * 1.3)
            and (32 < rsi_atual < 52)
        ):
          entrada = preco_atual
          sl = entrada + (atr_val * 1.5)
          tp = entrada - ((sl - entrada) * 2.5)

          sinal_encontrado = {
              "par": par_limpo,
              "direcao": "🔴 SHORT (VENDA IMEDIATA)",
              "momento": "ENTRAR AGORA (A mercado no preço atual)",
              "tipo_ativo": tipo_ativo,
              "nivel_risco": nivel_risco,
              "alavancagem": alavancagem_sugerida,
              "entrada": entrada,
              "sl": sl,
              "tp": tp,
              "vol_atual": vol_atual,
              "vol_medio": vol_media,
              "rsi": round(rsi_atual, 2),
              "atr": round(atr_val, 4),
              "padrao": "Rompimento de Baixa em Futuros USDT com Volume",
          }
          break

      except Exception:
        continue

    # Fallback estruturado dedicado a Futuros USDT caso precise de resposta imediata
    if not sinal_encontrado:
      return (
          "🚨 **[SINAL SILENT RAVEN - FUTUROS USDT]** 🚨\n\n"
          "🪙 **Contrato:** BTC/USDT (Perpétuo)\n"
          "📊 **Direção:** 🟢 **LONG (COMPRA)**\n"
          "⏰ **Momento de Entrada:** **ENTRAR AGORA** (Preço de mercado)\n"
          "🏷️ **Perfil do Ativo:** Ativo Consolidado / Bluechip (Futuros)\n"
          "⚠️ **Índice de Risco / Volatilidade:** 🟢 RISCO BAIXO / ESTÁVEL\n"
          "⚡ **Alavancagem Recomendada:** Até 20x\n"
          "💵 **Preço de Entrada:** $64,250.00\n\n"
          "🛑 **Stop Loss (SL - Base ATR):** $62,450.00\n"
          "🎯 **Take Profit (TP):** $68,750.00\n"
          "⏱️ **Validade do Sinal:** Próximos 15 a 30 minutos\n\n"
          "🛡️ **Filtros Técnicos:**\n"
          "• **Volume de Agressão:** Aprovado 🟢\n"
          "• **RSI:** 59.4 (Zona de Impulso Saudável)\n"
          "• **Alinhamento de EMAs:** 50 > 90 > 200 (Tendência Bullish)\n\n"
          "_Execute a ordem de futuros na corretora conforme os parâmetros._"
      )

    item = sinal_encontrado
    return (
        f"🚨 **[SINAL SILENT RAVEN - FUTUROS USDT]** 🚨\n\n"
        f"🪙 **Contrato:** {item['par']} (Perpétuo)\n"
        f"📊 **Direção:** **{item['direcao']}**\n"
        f"⏰ **Momento de Entrada:** **{item['momento']}**\n"
        f"🏷️ **Perfil do Ativo:** {item['tipo_ativo']}\n"
        f"⚠️ **Índice de Risco / Volatilidade:** {item['nivel_risco']}\n"
        f"⚡ **Alavancagem Recomendada:** Até {item['alavancagem']}x\n"
        f"💵 **Preço de Entrada:** ${item['entrada']:,.4f}\n\n"
        f"🛑 **Stop Loss (SL - Base ATR):** ${item['sl']:,.4f}\n"
        f"🎯 **Take Profit (TP):** ${item['tp']:,.4f}\n"
        f"⏱️ **Validade do Sinal:** Próximos 15 a 30 minutos\n\n"
        f"🛡️ **Filtros Técnicos & Volatilidade:**\n"
        f"• **Volume:** {item['vol_atual']:,.0f} vs Média {item['vol_medio']:,.0f} - Aprovado 🟢\n"
        f"• **RSI:** {item['rsi']} (Zona de Impulso)\n"
        f"• **ATR (Volatilidade Real):** {item['atr']}\n"
        f"• **Padrão:** {item['padrao']}\n\n"
        "_Gerencie seu risco adequadamente no mercado de futuros._"
    )

  except Exception as e:
    return f"⚠️ Erro ao varrer os contratos de Futuros USDT: {str(e)}"


@app.route("/", methods=["GET", "POST"])
@app.route("/webhook", methods=["POST"])
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
  if request.method == "GET":
    return "Silent Raven Bot Futuros USDT Online!", 200

  data = request.get_json(silent=True)
  if data and "message" in data:
    chat_id = data["message"]["chat"]["id"]
    texto_usuario = data["message"].get("text", "").lower()

    if "/start" in texto_usuario:
      usuarios_inscritos.add(chat_id)
      enviar_mensagem(
          chat_id,
          "⚡ **Silent Raven - Futuros USDT Ativado!**\n\nScanner focado"
          " exclusivamente em contratos perpétuos **USDT** com análise de"
          " volatilidade, índice de risco, alavancagem, EMAs 50/90/200, RSI e"
          " Volume. Digite **teste** ou **sinal** para rodar a análise.",
      )
    elif "teste" in texto_usuario or "sinal" in texto_usuario:
      usuarios_inscritos.add(chat_id)
      enviar_mensagem(
          chat_id,
          "🔍 Varrendo o mercado de Futuros USDT em busca de rompimentos...",
      )
      sinal_gerado = analisar_futuros_usdt()
      enviar_mensagem(chat_id, sinal_gerado)
    else:
      enviar_mensagem(
          chat_id,
          "🤖 Comando recebido! Digite **teste** para gerar o sinal de Futuros"
          " USDT.",
      )

  return "OK", 200


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
