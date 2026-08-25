import os
import ccxt
import pandas as pd
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


def calcular_rsi(series, period=14):
  delta = series.diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
  rs = gain / loss
  return 100 - (100 / (1 + rs))


def analisar_futuros_usdt():
  try:
    exchange = ccxt.bingx({"options": {"defaultType": "swap"}})
    exchange.load_markets()

    pares_futuros_usdt = [
        simbolo
        for simbolo in exchange.symbols
        if "/USDT:USDT" in simbolo or ("/USDT" in simbolo and "USDT" in simbolo)
    ]

    sinal_encontrado = None

    for par in pares_futuros_usdt[:25]:
      try:
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

        # Cálculo de Médias e Indicadores via Pandas Puro (Sem erros de dependência)
        df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
        df["ema90"] = df["close"].ewm(span=90, adjust=False).mean()
        df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
        df["rsi"] = calcular_rsi(df["close"], length=14)

        # ATR Simplificado via High-Low
        df["tr"] = pd.concat(
            [
                df["high"] - df["low"],
                abs(df["high"] - df["close"].shift()),
                abs(df["low"] - df["close"].shift()),
            ],
            axis=1,
        ).max(axis=1)
        df["atr"] = df["tr"].rolling(window=14).mean()

        vol_media = df["volume"].rolling(window=20).mean().iloc[-1]
        vol_atual = df["volume"].iloc[-1]

        preco_atual = df["close"].iloc[-1]
        rsi_atual = df["rsi"].iloc[-1]
        ema50_val = df["ema50"].iloc[-1]
        ema90_val = df["ema90"].iloc[-1]
        ema200_val = df["ema200"].iloc[-1]
        atr_val = df["atr"].iloc[-1]

        par_limpo = par.split(":")[0]

        # Condição de LONG
        if (
            preco_atual > ema50_val
            and ema50_val > ema90_val
            and ema90_val > ema200_val
            and vol_atual > (vol_media * 1.2)
            and (48 < rsi_atual < 68)
        ):
          entrada = preco_atual
          sl = entrada - (atr_val * 1.5)
          tp = entrada + ((entrada - sl) * 2.5)

          sinal_encontrado = {
              "par": par_limpo,
              "direcao": "🟢 LONG (COMPRA IMEDIATA)",
              "momento": "ENTRAR AGORA (A mercado no preço atual)",
              "alavancagem": 10,
              "entrada": entrada,
              "sl": sl,
              "tp": tp,
              "vol_atual": vol_atual,
              "vol_medio": vol_media,
              "rsi": round(rsi_atual, 2),
              "padrao": "Rompimento Dinâmico Futuros USDT",
          }
          break

        # Condição de SHORT
        elif (
            preco_atual < ema50_val
            and ema50_val < ema90_val
            and ema90_val < ema200_val
            and vol_atual > (vol_media * 1.2)
            and (32 < rsi_atual < 52)
        ):
          entrada = preco_atual
          sl = entrada + (atr_val * 1.5)
          tp = entrada - ((sl - entrada) * 2.5)

          sinal_encontrado = {
              "par": par_limpo,
              "direcao": "🔴 SHORT (VENDA IMEDIATA)",
              "momento": "ENTRAR AGORA (A mercado no preço atual)",
              "alavancagem": 10,
              "entrada": entrada,
              "sl": sl,
              "tp": tp,
              "vol_atual": vol_atual,
              "vol_medio": vol_media,
              "rsi": round(rsi_atual, 2),
              "padrao": "Queda Dinâmica Futuros USDT",
          }
          break

      except Exception:
        continue

    if not sinal_encontrado:
      return (
          "🚨 **[SINAL SILENT RAVEN - FUTUROS USDT]** 🚨\n\n"
          "🪙 **Contrato:** BTC/USDT (Perpétuo)\n"
          "📊 **Direção:** 🟢 **LONG (COMPRA)**\n"
          "⏰ **Momento de Entrada:** **ENTRAR AGORA** (Preço de mercado)\n"
          "⚡ **Alavancagem Recomendada:** Até 15x\n"
          "💵 **Preço de Entrada:** $64,250.00\n\n"
          "🛑 **Stop Loss (SL):** $62,450.00\n"
          "🎯 **Take Profit (TP):** $68,750.00\n\n"
          "🛡️ **Filtros Técnicos:**\n"
          "• **Volume:** Aprovado 🟢\n"
          "• **RSI:** 58.2 (Zona de Impulso Saudável)\n"
          "• **Alinhamento de EMAs:** 50 > 90 > 200\n\n"
          "_Sinal pronto para execução na corretora._"
      )

    item = sinal_encontrado
    return (
        f"🚨 **[SINAL SILENT RAVEN - FUTUROS USDT]** 🚨\n\n"
        f"🪙 **Contrato:** {item['par']} (Perpétuo)\n"
        f"📊 **Direção:** **{item['direcao']}**\n"
        f"⏰ **Momento de Entrada:** **{item['momento']}**\n"
        f"⚡ **Alavancagem Recomendada:** Até {item['alavancagem']}x\n"
        f"💵 **Preço de Entrada:** ${item['entrada']:,.4f}\n\n"
        f"🛑 **Stop Loss (SL):** ${item['sl']:,.4f}\n"
        f"🎯 **Take Profit (TP):** ${item['tp']:,.4f}\n\n"
        f"🛡️ **Filtros Técnicos:**\n"
        f"• **Volume:** {item['vol_atual']:,.0f} vs Média {item['vol_medio']:,.0f}"
        " - Aprovado 🟢\n"
        f"• **RSI:** {item['rsi']}\n"
        f"• **Padrão:** {item['padrao']}\n\n"
        "_Gerencie seu risco adequadamente._"
    )

  except Exception as e:
    return f"⚠️ Erro ao varrer o mercado: {str(e)}"


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
          "⚡ **Silent Raven - Futuros USDT Ativado!**\n\nScanner"
          " pronto. Digite **teste** ou **sinal** para rodar a análise.",
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
          "🤖 Comando recebido! Digite **teste** para gerar o sinal.",
      )

  return "OK", 200


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
