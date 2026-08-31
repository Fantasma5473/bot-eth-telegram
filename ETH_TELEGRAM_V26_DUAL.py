import os
import time
import requests
import pandas as pd
import numpy as np
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==========================================
# 1. SERVIDOR HTTP DE SAÚDE (PARA O RENDER)
# ==========================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot ETH Telegram rodando perfeitamente!")

def run_health_check_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"--> Servidor HTTP de Health Check rodando na porta {port}")
    server.serve_forever()

# Inicia o servidor HTTP em uma thread secundária para não travar o bot
threading.Thread(target=run_health_check_server, daemon=True).start()

# ==========================================
# 2. CONFIGURAÇÕES DO TELEGRAM E BINANCE
# ==========================================
# Insira seus dados abaixo se não estiver usando variáveis de ambiente
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "SEU_TOKEN_AQUI")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "SEU_CHAT_ID_AQUI")

SYMBOL = "ETHUSDT"
INTERVAL = "15m"
CHECK_INTERVAL = 60  # Verifica a cada 60 segundos

def send_telegram_message(message):
    """Envia mensagem para o Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Erro ao enviar mensagem no Telegram: {e}")
        return None

def get_binance_klines(symbol=SYMBOL, interval=INTERVAL, limit=100):
    """Obtém dados históricos de velas (candles) da Binance"""
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        return df
    except Exception as e:
        print(f"Erro ao obter dados da Binance: {e}")
        return None

def calculate_indicators(df):
    """Calcula as médias móveis e RSI (Indicadores)"""
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()
    
    # Cálculo do RSI 14
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

# ==========================================
# 3. LOOP PRINCIPAL DO BOT
# ==========================================
def main():
    print("--> Bot ETH Telegram iniciado com sucesso!")
    send_telegram_message("🚀 *Bot ETH iniciado e rodando 24/7 na nuvem!*")
    
    last_signal = None

    while True:
        try:
            df = get_binance_klines()
            if df is not None and not df.empty:
                df = calculate_indicators(df)
                
                last_row = df.iloc[-1]
                prev_row = df.iloc[-2]
                
                price = last_row['close']
                ema9 = last_row['EMA_9']
                ema21 = last_row['EMA_21']
                rsi = last_row['RSI']
                
                prev_ema9 = prev_row['EMA_9']
                prev_ema21 = prev_row['EMA_21']
                
                # Condição de COMPRA (Cruzamento de Alta)
                if prev_ema9 <= prev_ema21 and ema9 > ema21:
                    if last_signal != "BUY":
                        msg = (
                            f"🟢 *SINAL DE COMPRA (LONG) - ETH/USDT*\n\n"
                            f"💰 *Preço Atual:* ${price:.2f}\n"
                            f"📊 *RSI (14):* {rsi:.1f}\n"
                            f"📈 *EMA 9 cruzou acima da EMA 21*"
                        )
                        send_telegram_message(msg)
                        last_signal = "BUY"
                
                # Condição de VENDA (Cruzamento de Baixa)
                elif prev_ema9 >= prev_ema21 and ema9 < ema21:
                    if last_signal != "SELL":
                        msg = (
                            f"🔴 *SINAL DE VENDA (SHORT) - ETH/USDT*\n\n"
                            f"💰 *Preço Atual:* ${price:.2f}\n"
                            f"📊 *RSI (14):* {rsi:.1f}\n"
                            f"📉 *EMA 9 cruzou abaixo da EMA 21*"
                        )
                        send_telegram_message(msg)
                        last_signal = "SELL"

        except Exception as e:
            print(f"Erro na execução do loop: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
