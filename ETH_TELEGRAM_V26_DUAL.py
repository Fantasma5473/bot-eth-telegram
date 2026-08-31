import os
import time
import requests
import pandas as pd
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==========================================
# 1. SERVIDOR HTTP DE SAÚDE (RENDER FIX)
# ==========================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot V26 Ultra Rodando!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

def run_health_check_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# ==========================================
# 2. CONFIGURAÇÕES TELEGRAM E BINANCE
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

def get_binance_klines(symbol="ETHUSDT", interval="1m", limit=50):
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

def calculate_rsi(df, window=7):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

# ==========================================
# 3. MOTOR DE SINAIS E RESULTADO AUTOMÁTICO
# ==========================================
def run_trading_engine():
    print("--> Engine V26 M1 Ultra Rodando")
    last_signal_candle = None
    active_trade = None

    while True:
        try:
            df = get_binance_klines()
            if df is not None and len(df) >= 15:
                df = calculate_rsi(df)
                
                closed_candle = df.iloc[-2]
                candle_time = closed_candle['timestamp']
                price = closed_candle['close']
                rsi = closed_candle['RSI']

                # 1. VALIDA O RESULTADO DA OPERAÇÃO ANTERIOR
                if active_trade is not None and active_trade.get("target_candle") == candle_time:
                    entry = active_trade['entry']
                    direction = active_trade['direction']
                    
                    if direction == "CALL":
                        if price > entry:
                            send_telegram_message(f"🟢 *[WIN - COMPRA]*\n💰 Entrada: ${entry:.2f} | Fechamento: ${price:.2f}")
                        else:
                            send_telegram_message(f"🔴 *[LOSS - COMPRA]*\n💰 Entrada: ${entry:.2f} | Fechamento: ${price:.2f}")
                    elif direction == "PUT":
                        if price < entry:
                            send_telegram_message(f"🟢 *[WIN - VENDA]*\n💰 Entrada: ${entry:.2f} | Fechamento: ${price:.2f}")
                        else:
                            send_telegram_message(f"🔴 *[LOSS - VENDA]*\n💰 Entrada: ${entry:.2f} | Fechamento: ${price:.2f}")
                    
                    active_trade = None

                # 2. DISPARA NOVO SINAL (RSI <= 35 COMPRA / RSI >= 65 VENDA)
                if last_signal_candle != candle_time and active_trade is None:
                    if rsi <= 35:
                        send_telegram_message(f"⚡ *[M1] SINAL: CALL (COMPRA)*\n💰 *Preço:* ${price:.2f}\n📊 *RSI(7):* {rsi:.1f}\n⏳ *Expiração:* 1 Minuto")
                        # Alvo de validação = próximo candle fechado
                        next_candle_time = candle_time + 60000
                        active_trade = {"direction": "CALL", "entry": price, "target_candle": next_candle_time}
                        last_signal_candle = candle_time
                    elif rsi >= 65:
                        send_telegram_message(f"⚡ *[M1] SINAL: PUT (VENDA)*\n💰 *Preço:* ${price:.2f}\n📊 *RSI(7):* {rsi:.1f}\n⏳ *Expiração:* 1 Minuto")
                        next_candle_time = candle_time + 60000
                        active_trade = {"direction": "PUT", "entry": price, "target_candle": next_candle_time}
                        last_signal_candle = candle_time

        except Exception as e:
            print(f"Erro no Loop: {e}")

        time.sleep(5)

if __name__ == "__main__":
    send_telegram_message("🚀 *Bot V26 M1 Ultra Atualizado!*\n⚡ Filtro RSI(7): ≤ 35 (CALL) / ≥ 65 (PUT)\n🎯 Validação de WIN/LOSS na vela seguinte.")
    run_trading_engine()
