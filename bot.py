import os
import threading
import time
import ccxt
import pandas as pd
import requests
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


def enviar_mensagem(chat_id, texto):
  if not chat_id:
    return
  url = f"{TELEGRAM_API_URL}/sendMessage"
  payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}
  try:
    requests.post(url, json=payload, timeout=10)
  except Exception as e:
    print(f"Erro ao enviar mensagem: {e}")


def calcular_rsi(series, period=14):
  delta = series.diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
  rs = gain / loss
  return 100 - (100 / (1 + rs))


def analisar_e_gerar_sinal():
  try:
    exchange = ccxt.bingx({"options": {"defaultType": "swap"}})
    exchange.load_markets()

    pares_futuros_usdt = [
        simbolo
        for simbolo in exchange.symbols
        if "/USDT:USDT" in simbolo or ("/USDT" in simbolo and "USDT" in simbolo)
    ]

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

        df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
        df["ema90"] = df["close"].ewm(span=90, adjust=False).mean()
        df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
        df["rsi"] = calcular_rsi(df["close"], length=14)

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

          return (
              f"🚨 **[SINAL SILENT RAVEN - FUTUROS USDT]** 🚨\n\n"
              f"🪙 **Contrato:** {par_limpo} (Perpétuo)\n"
              f"📊 **Direção:** 🟢 **LONG (COMPRA IMEDIATA)**\n"
              f"⚡ **Alavancagem:** Até 10x\n"
              f"💵 **Entrada:** ${entrada:,.4f}\n"
              f"🛑 **Stop Loss:** ${sl:,.4f}\n"
              f"🎯 **Take Profit:** ${tp:,.4f}\n\n"
              f"🛡️ **RSI:** {round(rsi_atual, 2)} | **Volume Aprovado 🟢**"
          )

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

          return (
              f"🚨 **[SINAL SILENT RAVEN - FUTUROS USDT]** 🚨\n\n"
              f"🪙 **Contrato:** {par_limpo} (Perpétuo)\n"
              f"📊 **Direção:** 🔴 **SHORT (VENDA IMEDIATA)**\n"
              f"⚡ **Alavancagem:** Até 10x\n"
              f"💵 **Entrada:** ${entrada:,.4f}\n"
              f"🛑 **Stop Loss:** ${sl:,.4f}\n"
              f"🎯 **Take Profit:** ${tp:,.4f}\n\n"
              f"🛡️ **RSI:** {round(rsi_atual, 2)} | **Volume Aprovado 🟢**"
          )
      except Exception:
        continue

    return None
  except Exception as e:
    print(f"Erro na varredura: {e}")
    return None


# Loop automático rodando em segundo plano
def loop_automatico():
  time.sleep(10)  # Aguarda o bot iniciar por completo
  while True:
    try:
      print("Executando varredura automática...")
      sinal = analisar_e_gerar_sinal()
      if sinal and TELEGRAM_CHAT_ID:
        enviar_mensagem(TELEGRAM_CHAT_ID, sinal)
    except Exception as e:
      print(f"Erro no loop: {e}")

    # Intervalo entre as varreduras automáticas (ex: a cada 30 minutos = 1800 segundos)
    time.sleep(1800)


# Inicia a thread automática em paralelo com o Web Server
t = threading.Thread(target=loop_automatico)
t.daemon = True
t.start()


@app.route("/", methods=["GET", "POST"])
def webhook():
  if request.method == "GET":
    return "Silent Raven Bot Automático Online!", 200

  data = request.get_json(silent=True)
  if data and "message" in data:
    chat_id = data["message"]["chat"]["id"]
    texto = data["message"].get("text", "").lower()
    if "teste" in texto or "sinal" in texto:
      enviar_mensagem(chat_id, "🔍 Varrendo o mercado manualmente...")
      res = analisar_e_gerar_sinal()
      if res:
        enviar_mensagem(chat_id, res)
      else:
        enviar_mensagem(
            chat_id, "⚠️ Nenhum padrão ideal encontrado no momento."
        )

  return "OK", 200


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
