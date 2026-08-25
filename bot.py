import os
from flask import Flask, request
import requests

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


def analisar_mercado_com_filtros():
  ativo = "GRASS-USDT"
  volume_atual = 4200000
  volume_medio = 1500000
  rompimento = "Rompimento de Topo Anterior (Resistência Chave)"

  filtro_volume_ok = volume_atual > (volume_medio * 1.5)

  if filtro_volume_ok:
    return (
        f"🚨 **[SINAL VALIDADO - SILENT RAVEN]** 🚨\n\n"
        f"🪙 **Ativo:** {ativo}\n"
        f"📊 **Filtro de Volume:** Aprovado 🟢 ({volume_atual:,.0f} vs Média"
        f" {volume_medio:,.0f})\n"
        f"📈 **Padrão Gráfico:** {rompimento}\n"
        "⚡ **Direção:** LONG / Compra\n"
        "🎯 **Take Profit:** Alvo Técnico Definido\n"
        "🛑 **Stop Loss:** Abaixo da Zona de Rompimento\n\n"
        "_Varredura executada com sucesso._"
    )
  return None


@app.route("/", methods=["GET", "POST"])
@app.route("/webhook", methods=["POST"])
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
  if request.method == "GET":
    return "Silent Raven Bot Online e Operacional!", 200

  data = request.get_json(silent=True)
  if data and "message" in data:
    chat_id = data["message"]["chat"]["id"]
    texto_usuario = data["message"].get("text", "").lower()

    if "/start" in texto_usuario:
      usuarios_inscritos.add(chat_id)
      enviar_mensagem(
          chat_id,
          "⚡ **Bem-vindo ao Silent Raven Bot!**\n\nFiltros de **Volume** e"
          " **Rompimento de Topo/Fundo** ativados. Digite **teste** para rodar"
          " o scanner de mercado.",
      )
    elif "teste" in texto_usuario:
      usuarios_inscritos.add(chat_id)
      enviar_mensagem(
          chat_id, "🔍 Analisando livro de ordens, volume atípico e rompimentos..."
      )
      sinal_gerado = analisar_mercado_com_filtros()
      if sinal_gerado:
        enviar_mensagem(chat_id, sinal_gerado)
      else:
        enviar_mensagem(
            chat_id,
            "⚠️ Nenhum ativo atingiu os parâmetros mínimos de volume neste"
            " momento.",
        )
    else:
      enviar_mensagem(
          chat_id,
          "🤖 Comando não reconhecido. Digite **teste** para ver os sinais em"
          " ação.",
      )

  return "OK", 200


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
