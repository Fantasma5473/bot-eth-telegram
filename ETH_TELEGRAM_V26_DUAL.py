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
        self.wfile.write(b"Bots Conservador e Agressivo rodando!")

def run_health_check_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# ==========================================
# 2. CONFIGURAÇÕES COMPARTILHADAS
# ==========================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "SEU_TOKEN_AQUI")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "SEU_CHAT_ID_AQUI")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erro no Telegram: {e}")

def get_binance_klines(symbol="ETHUSDT", interval="15m", limit=100):
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
        return df
    except Exception as e:
        print(f"Erro Binance: {e}")
        return None

def calculate_indicators(df):
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

# ==========================================
# 3. MODO CONSERVADOR (Gráfico de 1 Hora)
# ==========================================
def run_conservador():
    print("--> Perfil CONSERVADOR ativo (TF: 1h)")
    last_signal = None
    while True:
        try:
            df = get_binance_klines(interval="1h")
            if df is not None and not df.empty:
                df = calculate_indicators(df)
                last = df.iloc[-1]
                prev = df.iloc[-2]
                
                if prev['EMA_9'] <= prev['EMA_21'] and last['EMA_9'] > last['EMA_21']:
                    if last_signal != "BUY":
                        msg = f"🛡️ *[CONSERVADOR - 1H] COMPRA ETH/USDT*\n💰 Preço: ${last['close']:.2f}\n📊 RSI: {last['RSI']:.1f}"
                        send_telegram_message(msg)
                        last_signal = "BUY"
                elif prev['EMA_9'] >= prev['EMA_21'] and last['EMA_9'] < last['EMA_21']:
                    if last_signal != "SELL":
                        msg = f"🛡️ *[CONSERVADOR - 1H] VENDA ETH/USDT*\n💰 Preço: ${last['close']:.2f}\n📊 RSI: {last['RSI']:.1f}"
                        send_telegram_message(msg)
                        last_signal = "SELL"
        except Exception as e:
            print(f"Erro Conservador: {e}")
        time.sleep(60)

# ==========================================
# 4. MODO AGRESSIVO (Gráfico de 15 Minutos)
# ==========================================
def run_agressivo():
    print("--> Perfil AGRESSIVO ativo (TF: 15m)")
    last_signal = None
    while True:
        try:
            df = get_binance_klines(interval="15m")
            if df is not None and not df.empty:
                df = calculate_indicators(df)
                last = df.iloc[-1]
                prev = df.iloc[-2]
                
                if prev['EMA_9'] <= prev['EMA_21'] and last['EMA_9'] > last['EMA_21']:
                    if last_signal != "BUY":
                        msg = f"⚡ *[AGRESSIVO - 15M] COMPRA ETH/USDT*\n💰 Preço: ${last['close']:.2f}\n📊 RSI: {last['RSI']:.1f}"
                        send_telegram_message(msg)
                        last_signal = "BUY"
                elif prev['EMA_9'] >= prev['EMA_21'] and last['EMA_9'] < last['EMA_21']:
                    if last_signal != "SELL":
                        msg = f"⚡ *[AGRESSIVO - 15M] VENDA ETH/USDT*\n💰 Preço: ${last['close']:.2f}\n📊 RSI: {last['RSI']:.1f}"
                        send_telegram_message(msg)
                        last_signal = "SELL"
        except Exception as e:
            print(f"Erro Agressivo: {e}")
        time.sleep(60)

# ==========================================
# 5. EXECUÇÃO PARALELA DUAL
# ==========================================
if __name__ == "__main__":
    send_telegram_message("🚀 *Sistema DUAL Conectado!*\n🛡️ Modo Conservador (1h) ON\n⚡ Modo Agressivo (15m) ON")
    
    t_conservador = threading.Thread(target=run_conservador)
    t_agressivo = threading.Thread(target=run_agressivo)
    
    t_conservador.start()
    t_agressivo.start()
