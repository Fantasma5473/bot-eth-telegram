import os
import time
import requests
import pandas as pd
import numpy as np
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
        self.wfile.write(b"Bot V26 Exaustao M1 (Dual Telegram) Rodando!")

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

def get_binance_klines(symbol="ETHUSDT", interval="1m", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        return df
    except Exception as e:
        print(f"Erro Binance: {e}")
        return None

def calculate_indicators(df):
    # RSI (7)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=7).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=7).mean()
    rs = gain / loss
    df['RSI7'] = 100 - (100 / (1 + rs))

    # BBZ (Bollinger Band Z-Score 20)
    sma20 = df['close'].rolling(window=20).mean()
    std20 = df['close'].rolling(window=20).std()
    df['BBZ'] = (df['close'] - sma20) / std20

    # Volume Relativo
    vol_sma20 = df['volume'].rolling(window=20).mean()
    df['VOL_REL'] = df['volume'] / vol_sma20

    # Contagem de Velas Seguidas da mesma cor
    df['is_green'] = df['close'] > df['open']
    df['is_red'] = df['close'] < df['open']
    
    velas_seguidas = []
    count = 0
    last_dir = None
    for idx, row in df.iterrows():
        if row['is_green']:
            curr_dir = 'green'
        elif row['is_red']:
            curr_dir = 'red'
        else:
            curr_dir = None

        if curr_dir == last_dir and curr_dir is not None:
            count += 1
        else:
            count = 1 if curr_dir is not None else 0
            last_dir = curr_dir
        velas_seguidas.append(count)
    df['VELAS_SEGUIDAS'] = velas_seguidas

    return df

# ==========================================
# 3. MOTOR DE NEGOCIAÇÃO M1 (DUAL)
# ==========================================
def run_trading_engine():
    print("--> Engine V26 M1 Dual Iniciado")
    last_signal_time_agressivo = None
    last_signal_time_conservador = None
    
    active_trade_agressivo = None
    active_trade_conservador = None

    while True:
        try:
            df = get_binance_klines(interval="1m")
            if df is not None and len(df) >= 30:
                df = calculate_indicators(df)
                last = df.iloc[-2]  # Candle recém-fechado
                current_time = last['timestamp']
                current_price = last['close']

                # --- VALIDAR RESULTADO AGRESSIVO (1 MINUTO) ---
                if active_trade_agressivo is not None:
                    entry = active_trade_agressivo['entry_price']
                    direction = active_trade_agressivo['direction']
                    if (direction == "CALL" and current_price > entry) or (direction == "PUT" and current_price < entry):
                        send_telegram_message(f"🟢 *[WIN - AGRESSIVO M1]*\n💰 Entrada: ${entry:.2f} | Fechamento: ${current_price:.2f}")
                    else:
                        send_telegram_message(f"🔴 *[LOSS - AGRESSIVO M1]*\n💰 Entrada: ${entry:.2f} | Fechamento: ${current_price:.2f}")
                    active_trade_agressivo = None

                # --- VALIDAR RESULTADO CONSERVADOR (1 MINUTO) ---
                if active_trade_conservador is not None:
                    entry = active_trade_conservador['entry_price']
                    direction = active_trade_conservador['direction']
                    if (direction == "CALL" and current_price > entry) or (direction == "PUT" and current_price < entry):
                        send_telegram_message(f"🟢 *[WIN - CONSERVADOR M1]*\n💰 Entrada: ${entry:.2f} | Fechamento: ${current_price:.2f}")
                    else:
                        send_telegram_message(f"🔴 *[LOSS - CONSERVADOR M1]*\n💰 Entrada: ${entry:.2f} | Fechamento: ${current_price:.2f}")
                    active_trade_conservador = None

                # --- GERAR SINAIS MODO AGRESSIVO (M1) ---
                if last_signal_time_agressivo != current_time:
                    if last['RSI7'] <= 30 or last['BBZ'] <= -1.8:
                        active_trade_agressivo = {"direction": "CALL", "entry_price": current_price}
                        msg = (
                            f"⚡ *[AGRESSIVO - M1] SINAL: CALL (COMPRA)*\n"
                            f"💰 *Entrada:* ${current_price:.2f}\n"
                            f"📊 *RSI(7):* {last['RSI7']:.1f} | *BBZ:* {last['BBZ']:.2f}\n"
                            f"📈 *Vol Rel:* {last['VOL_REL']:.2f}x | *Velas Seguidas:* {last['VELAS_SEGUIDAS']}\n"
                            f"⏳ *Expiração:* Final da Vela (1m)"
                        )
                        send_telegram_message(msg)
                        last_signal_time_agressivo = current_time

                    elif last['RSI7'] >= 70 or last['BBZ'] >= 1.8:
                        active_trade_agressivo = {"direction": "PUT", "entry_price": current_price}
                        msg = (
                            f"⚡ *[AGRESSIVO - M1] SINAL: PUT (VENDA)*\n"
                            f"💰 *Entrada:* ${current_price:.2f}\n"
                            f"📊 *RSI(7):* {last['RSI7']:.1f} | *BBZ:* {last['BBZ']:.2f}\n"
                            f"📈 *Vol Rel:* {last['VOL_REL']:.2f}x | *Velas Seguidas:* {last['VELAS_SEGUIDAS']}\n"
                            f"⏳ *Expiração:* Final da Vela (1m)"
                        )
                        send_telegram_message(msg)
                        last_signal_time_agressivo = current_time

                # --- GERAR SINAIS MODO CONSERVADOR (M1) ---
                if last_signal_time_conservador != current_time:
                    if last['RSI7'] <= 22 and last['BBZ'] <= -2.1:
                        active_trade_conservador = {"direction": "CALL", "entry_price": current_price}
                        msg = (
                            f"🛡️ *[CONSERVADOR - M1] SINAL: CALL (COMPRA)*\n"
                            f"💰 *Entrada:* ${current_price:.2f}\n"
                            f"📊 *RSI(7):* {last['RSI7']:.1f} | *BBZ:* {last['BBZ']:.2f}\n"
                            f"📈 *Vol Rel:* {last['VOL_REL']:.2f}x | *Velas Seguidas:* {last['VELAS_SEGUIDAS']}\n"
                            f"⏳ *Expiração:* Final da Vela (1m)"
                        )
                        send_telegram_message(msg)
                        last_signal_time_conservador = current_time

                    elif last['RSI7'] >= 78 and last['BBZ'] >= 2.1:
                        active_trade_conservador = {"direction": "PUT", "entry_price": current_price}
                        msg = (
                            f"🛡️ *[CONSERVADOR - M1] SINAL: PUT (VENDA)*\n"
                            f"💰 *Entrada:* ${current_price:.2f}\n"
                            f"📊 *RSI(7):* {last['RSI7']:.1f} | *BBZ:* {last['BBZ']:.2f}\n"
                            f"📈 *Vol Rel:* {last['VOL_REL']:.2f}x | *Velas Seguidas:* {last['VELAS_SEGUIDAS']}\n"
                            f"⏳ *Expiração:* Final da Vela (1m)"
                        )
                        send_telegram_message(msg)
                        last_signal_time_conservador = current_time

        except Exception as e:
            print(f"Erro Engine M1: {e}")
        time.sleep(5)

# ==========================================
# 4. EXECUÇÃO
# ==========================================
if __name__ == "__main__":
    send_telegram_message("🚀 *Bot V26 Exaustão M1 DUAL Atualizado com Sucesso!*\n⚡ Agressivo: RSI(7) ≤ 30 / ≥ 70 (~63 sinais/dia)\n🛡️ Conservador: RSI(7) ≤ 22 / ≥ 78 (~26 sinais/dia)\n⏳ Expiração: 1 Minuto para Opções Binárias.")
    run_trading_engine()
