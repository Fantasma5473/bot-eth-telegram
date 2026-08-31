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
        self.wfile.write(b"Bot Opcoes Binarias ETH rodando!")

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
# 3. MODO CONSERVADOR (Gráfico 1 Hora - Expiração 1H)
# ==========================================
def run_conservador():
    print("--> Perfil CONSERVADOR ativo (OPCÕES BINÁRIAS - 1H)")
    last_signal = None
    active_trade = None

    while True:
        try:
            df = get_binance_klines(interval="1h")
            if df is not None and not df.empty:
                df = calculate_indicators(df)
                last = df.iloc[-1]
                prev = df.iloc[-2]
                current_price = last['close']

                # Verifica resultado da operação de Opções Binárias no fechamento da vela
                if active_trade is not None:
                    entry_price = active_trade['entry_price']
                    direction = active_trade['direction']

                    if direction == "CALL/COMPRA":
                        if current_price > entry_price:
                            msg = f"🟢 *[WIN - CONSERVADOR 1H]*\n💰 *Entrada:* ${entry_price:.2f}\n🏁 *Fechamento:* ${current_price:.2f}\n✅ O preço final ficou ACIMA!"
                        else:
                            msg = f"🔴 *[LOSS - CONSERVADOR 1H]*\n💰 *Entrada:* ${entry_price:.2f}\n🏁 *Fechamento:* ${current_price:.2f}\n❌ O preço final ficou ABAIXO."
                        send_telegram_message(msg)
                    elif direction == "PUT/VENDA":
                        if current_price < entry_price:
                            msg = f"🟢 *[WIN - CONSERVADOR 1H]*\n💰 *Entrada:* ${entry_price:.2f}\n🏁 *Fechamento:* ${current_price:.2f}\n✅ O preço final ficou ABAIXO!"
                        else:
                            msg = f"🔴 *[LOSS - CONSERVADOR 1H]*\n💰 *Entrada:* ${entry_price:.2f}\n🏁 *Fechamento:* ${current_price:.2f}\n❌ O preço final ficou ACIMA."
                        send_telegram_message(msg)
                    
                    active_trade = None

                # Sinal de COMPRA (CALL)
                if prev['EMA_9'] <= prev['EMA_21'] and last['EMA_9'] > last['EMA_21']:
                    if last_signal != "BUY":
                        active_trade = {"direction": "CALL/COMPRA", "entry_price": current_price}
                        msg = f"🛡️ *[CONSERVADOR - 1H] SINAL: CALL (COMPRA)*\n💰 *Preço de Entrada:* ${current_price:.2f}\n📊 *RSI:* {last['RSI']:.1f}\n⏳ *Expiração:* Final da Vela de 1h"
                        send_telegram_message(msg)
                        last_signal = "BUY"

                # Sinal de VENDA (PUT)
                elif prev['EMA_9'] >= prev['EMA_21'] and last['EMA_9'] < last['EMA_21']:
                    if last_signal != "SELL":
                        active_trade = {"direction": "PUT/VENDA", "entry_price": current_price}
                        msg = f"🛡️ *[CONSERVADOR - 1H] SINAL: PUT (VENDA)*\n💰 *Preço de Entrada:* ${current_price:.2f}\n📊 *RSI:* {last['RSI']:.1f}\n⏳ *Expiração:* Final da Vela de 1h"
                        send_telegram_message(msg)
                        last_signal = "SELL"

        except Exception as e:
            print(f"Erro Conservador: {e}")
        time.sleep(60)

# ==========================================
# 4. MODO AGRESSIVO (Gráfico 15 Minutos - Expiração 15m)
# ==========================================
def run_agressivo():
    print("--> Perfil AGRESSIVO ativo (OPÇÕES BINÁRIAS - 15M)")
    last_signal = None
    active_trade = None

    while True:
        try:
            df = get_binance_klines(interval="15m")
            if df is not None and not df.empty:
                df = calculate_indicators(df)
                last = df.iloc[-1]
                prev = df.iloc[-2]
                current_price = last['close']

                # Verifica resultado da operação no fechamento
                if active_trade is not None:
                    entry_price = active_trade['entry_price']
                    direction = active_trade['direction']

                    if direction == "CALL/COMPRA":
                        if current_price > entry_price:
                            msg = f"🟢 *[WIN - AGRESSIVO 15M]*\n💰 *Entrada:* ${entry_price:.2f}\n🏁 *Fechamento:* ${current_price:.2f}\n✅ O preço final ficou ACIMA!"
                        else:
                            msg = f"🔴 *[LOSS - AGRESSIVO 15M]*\n💰 *Entrada:* ${entry_price:.2f}\n🏁 *Fechamento:* ${current_price:.2f}\n❌ O preço final ficou ABAIXO."
                        send_telegram_message(msg)
                    elif direction == "PUT/VENDA":
                        if current_price < entry_price:
                            msg = f"🟢 *[WIN - AGRESSIVO 15M]*\n💰 *Entrada:* ${entry_price:.2f}\n🏁 *Fechamento:* ${current_price:.2f}\n✅ O preço final ficou ABAIXO!"
                        else:
                            msg = f"🔴 *[LOSS - AGRESSIVO 15M]*\n💰 *Entrada:* ${entry_price:.2f}\n🏁 *Fechamento:* ${current_price:.2f}\n❌ O preço final ficou ACIMA."
                        send_telegram_message(msg)
                    
                    active_trade = None

                # Sinal de COMPRA (CALL)
                if prev['EMA_9'] <= prev['EMA_21'] and last['EMA_9'] > last['EMA_21']:
                    if last_signal != "BUY":
                        active_trade = {"direction": "CALL/COMPRA", "entry_price": current_price}
                        msg = f"⚡ *[AGRESSIVO - 15M] SINAL: CALL (COMPRA)*\n💰 *Preço de Entrada:* ${current_price:.2f}\n📊 *RSI:* {last['RSI']:.1f}\n⏳ *Expiração:* Final da Vela de 15m"
                        send_telegram_message(msg)
                        last_signal = "BUY"

                # Sinal de VENDA (PUT)
                elif prev['EMA_9'] >= prev['EMA_21'] and last['EMA_9'] < last['EMA_21']:
                    if last_signal != "SELL":
                        active_trade = {"direction": "PUT/VENDA", "entry_price": current_price}
                        msg = f"⚡ *[AGRESSIVO - 15M] SINAL: PUT (VENDA)*\n💰 *Preço de Entrada:* ${current_price:.2f}\n📊 *RSI:* {last['RSI']:.1f}\n⏳ *Expiração:* Final da Vela de 15m"
                        send_telegram_message(msg)
                        last_signal = "SELL"

        except Exception as e:
            print(f"Erro Agressivo: {e}")
        time.sleep(60)

# ==========================================
# 5. EXECUÇÃO PARALELA DUAL
# ==========================================
if __name__ == "__main__":
    send_telegram_message("📈 *Sistema DUAL para Opções Binárias Ativado!*\n🛡️ Conservador: Sinais em 1h (Expiração 1h)\n⚡ Agressivo: Sinais em 15m (Expiração 15m)\n🎯 Resultado (WIN / LOSS) ao final de cada vela.")
    
    t_conservador = threading.Thread(target=run_conservador)
    t_agressivo = threading.Thread(target=run_agressivo)
    
    t_conservador.start()
    t_agressivo.start()
