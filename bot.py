import os
import time
import requests
import ccxt
import pandas as pd

# Configurações do Telegram
TELEGRAM_BOT_TOKEN = "7544383186:AAH5T7Yf2oQ08w0Gj8i3p5e7z2x1c9v8b7n"
TELEGRAM_CHAT_ID = "8180604206"

def enviar_telegram(mensagem):
    """Envia mensagem de texto para o chat do Telegram configurado."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"Erro ao enviar mensagem Telegram: {response.text}")
    except Exception as e:
        print(f"Erro de conexão com Telegram: {e}")

def buscar_top_moedas(limite=30):
    """Busca as principais criptomoedas por volume na BingX."""
    try:
        exchange = ccxt.bingx({'enableRateLimit': True})
        markets = exchange.load_markets()
        simbolos = [
            symbol for symbol, market in markets.items() 
            if market['quote'] == 'USDT' and market.get('active', True) and '/USDT' in symbol
        ]
        return simbolos[:limite]
    except Exception as e:
        print(f"Erro ao buscar moedas na BingX: {e}")
        return []

def analisar_moeda(simbolo, timeframe='1h'):
    """Analisa o gráfico de uma moeda usando médias móveis calculadas nativamente."""
    try:
        exchange = ccxt.bingx({'enableRateLimit': True})
        ohclv = exchange.fetch_ohlcv(simbolo, timeframe=timeframe, limit=60)
        
        if len(ohclv) < 50:
            return None
            
        df = pd.DataFrame(ohclv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Cálculo nativo das Médias Móveis Exponenciais (EMA) via Pandas
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        atual = df.iloc[-2]
        anterior = df.iloc[-3]
        
        preco_atual = atual['close']
        e20_atual = atual['ema20']
        e50_atual = atual['ema50']
        e20_ant = anterior['ema20']
        e50_ant = anterior['ema50']
        
        alerta = None
        if e20_ant <= e50_ant and e20_atual > e50_atual:
            alerta = (
                f"🚀 *SINAL DE CRUZAMENTO DE ALTA (LONG)*\n\n"
                f"🔹 **Ativo:** `{simbolo}`\n"
                f"⏱ **Timeframe:** `{timeframe}`\n"
                f"💰 **Preço:** `{preco_atual}`\n"
                f"📈 EMA 20 cruzou acima da EMA 50!"
            )
        elif e20_ant >= e50_ant and e20_atual < e50_atual:
            alerta = (
                f"📉 *SINAL DE CRUZAMENTO DE BAIXA (SHORT)*\n\n"
                f"🔹 **Ativo:** `{simbolo}`\n"
                f"⏱ **Timeframe:** `{timeframe}`\n"
                f"💰 **Preço:** `{preco_atual}`\n"
                f"📉 EMA 20 cruzou abaixo da EMA 50!"
            )
            
        return alerta
    except Exception as e:
        print(f"Erro ao analisar o ativo {simbolo}: {e}")
        return None

if __name__ == "__main__":
    print("Iniciando Silent Raven Bot...")
    enviar_telegram("🤖 *Silent Raven Bot Ativo!* Monitorando o mercado em tempo real...")
    
    while True:
        try:
            moedas = buscar_top_moedas(30)
            for moeda in moedas:
                alerta = analisar_moeda(moeda, timeframe='1h')
                if alerta:
                    enviar_telegram(alerta)
                    time.sleep(2)
            time.sleep(900)
        except Exception as e:
            print(f"Erro no loop principal: {e}")
            time.sleep(60)
