import os
import time
import requests
import ccxt
import pandas as pd
import pandas_ta as ta

# Configurações do Telegram
TELEGRAM_BOT_TOKEN = "7544383186:AAH5T7Yf2oQ08w0Gj8i3p5e7z2x1c9v8b7n"  # Token atual do seu bot
TELEGRAM_CHAT_ID = "8180604206"  # Seu ID configurado diretamente

def enviar_telegram(mensagem):
    """Envia mensagem de texto para o chat do Telegram configurado."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Erro: Token ou Chat ID do Telegram não configurados.")
        return
    
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

def buscar_top_moedas(limite=40):
    """Busca as principais criptomoedas por volume na BingX."""
    try:
        exchange = ccxt.bingx({'enableRateLimit': True})
        markets = exchange.load_markets()
        
        # Filtra apenas pares USDT que estão ativos
        simbolos = [
            symbol for symbol, market in markets.items() 
            if market['quote'] == 'USDT' and market.get('active', True) and '/USDT' in symbol
        ]
        
        # Retorna a quantidade solicitada
        return simbolos[:limite]
    except Exception as e:
        print(f"Erro ao buscar moedas na BingX: {e}")
        return []

def analisar_moeda(simbolo, timeframe='1h'):
    """Analisa o gráfico de uma moeda usando indicadores técnicos."""
    try:
        exchange = ccxt.bingx({'enableRateLimit': True})
        ohclv = exchange.fetch_ohlcv(simbolo, timeframe=timeframe, limit=100)
        
        if len(ohclv) < 50:
            return None
            
        df = pd.DataFrame(ohclv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Cálculo de Indicadores Técnicos com pandas_ta
        df['rsi'] = ta.rsi(df['close'], length=14)
        ema20 = ta.ema(df['close'], length=20)
        ema50 = ta.ema(df['close'], length=50)
        
        if ema20 is None or ema50 is None or df['rsi'].empty:
            return None
            
        df['ema20'] = ema20
        df['ema50'] = ema50
        
        # Pega o último candle fechado
        atual = df.iloc[-2]
        preco_atual = atual['close']
        rsi_atual = atual['rsi']
        e20 = atual['ema20']
        e50 = atual['ema50']
        
        # Lógica de Alerta Simples (Cruzamento de Médias + RSI)
        alerta = None
        if e20 > e50 and rsi_atual < 40:
            alerta = (
                f"🚀 *SINAL DE COMPRA (LONG)*\n\n"
                f"🔹 **Ativo:** `{simbolo}`\n"
                f"⏱ **Timeframe:** `{timeframe}`\n"
                f"💰 **Preço:** `{preco_atual}`\n"
                f"📊 **RSI:** `{rsi_atual:.2f}`\n"
                f"📈 Tendência de alta com RSI oversold."
            )
        elif e20 < e50 and rsi_atual > 60:
            alerta = (
                f"📉 *SINAL DE VENDA (SHORT)*\n\n"
                f"🔹 **Ativo:** `{simbolo}`\n"
                f"⏱ **Timeframe:** `{timeframe}`\n"
                f"💰 **Preço:** `{preco_atual}`\n"
                f"📊 **RSI:** `{rsi_atual:.2f}`\n"
                f"📉 Tendência de baixa com RSI overbought."
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
            moedas = buscar_top_moedas(40)
            for moeda in moedas:
                alerta = analisar_moeda(moeda, timeframe='1h')
                if alerta:
                    enviar_telegram(alerta)
                    time.sleep(2)  # Pausa breve entre os envios para evitar bloqueio da API
            
            # Aguarda 15 minutos (900 segundos) antes da próxima varredura completa
            time.sleep(900)
        except Exception as e:
            print(f"Erro no loop principal: {e}")
            time.sleep(60)
