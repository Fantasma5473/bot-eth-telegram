import os
import time
import requests
import pandas as pd
import numpy as np
from flask import Flask
from threading import Thread

# ==========================================
# SERVIDOR WEB PARA RENDER FREE
# ==========================================
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return "Bot V26 Exaustao Pro Multi-Moedas Ativo!"

def keep_alive():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

# ==========================================
# TELEGRAM
# ==========================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8649783045:AAE2mxbkGREP3a6lrXWxh6nHaHEwfcCc5mg")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8704308638")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Erro Telegram: {e}")

# ==========================================
# INDICADORES DA BINANCE
# ==========================================
SYMBOLS = ["ETHUSDT", "BTCUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]

def get_binance_klines(symbol="ETHUSDT", interval="1m", limit=60):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        return df
    except Exception:
        return None

def process_indicators(df):
    df['candle_body'] = np.abs(df['close'] - df['open'])
    df['is_green'] = df['close'] > df['open']
    df['is_red'] = df['close'] < df['open']

    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    df['ATR14'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(14).mean()

    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(5).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(5).mean()
    df['RSI5'] = 100 - (100 / (1 + (gain / (loss + 1e-10))))

    sma20 = df['close'].rolling(20).mean()
    std20 = df['close'].rolling(20).std()
    df['BBZ'] = (df['close'] - sma20) / (std20 + 1e-10)

    vol_sma20 = df['volume'].rolling(20).mean()
    df['VOL_REL'] = df['volume'] / (vol_sma20 + 1e-10)

    consec = []
    c = 0
    last = None
    for g, r in zip(df['is_green'], df['is_red']):
        curr = 'G' if g else ('R' if r else 'D')
        if curr == last and curr != 'D':
            c += 1
        else:
            c = 1 if curr != 'D' else 0
            last = curr
        consec.append(c)
    df['consec'] = consec
    return df

# ==========================================
# LOOPS DE MONITORAMENTO
# ==========================================
def run_cloud_bot():
    send_telegram_message("🚀 *Bot Exaustão Pro Multi-Moedas Iniciado!*\nMonitorando: ETH, BTC, SOL, XRP, ADA.")
    
    last_signal = {s: None for s in SYMBOLS}
    last_hourly_ping = time.time()

    while True:
        # Envia um ping a cada 1 hora para confirmar que está ativo
        if time.time() - last_hourly_ping >= 3600:
            send_telegram_message("🟢 *[STATUS 24/7]*: Bot online e analisando 5 moedas na nuvem.")
            last_hourly_ping = time.time()

        for symbol in SYMBOLS:
            try:
                df = get_binance_klines(symbol)
                if df is not None and len(df) >= 30:
                    df = process_indicators(df)
                    closed = df.iloc[-2]
                    
                    price = closed['close']
                    rsi = closed['RSI5']
                    bbz = closed['BBZ']
                    vol = closed['VOL_REL']
                    consec = closed['consec']
                    body = closed['candle_body']
                    atr = closed['ATR14']

                    vol_ok = vol >= 1.3
                    body_ok = body >= (1.0 * atr)

                    if last_signal[symbol] != closed['timestamp']:
                        direction = None
                        if closed['is_red'] and consec >= 3 and rsi <= 20 and bbz <= -2.5 and vol_ok and body_ok:
                            direction = "CALL"
                        elif closed['is_green'] and consec >= 3 and rsi >= 80 and bbz >= 2.5 and vol_ok and body_ok:
                            direction = "PUT"

                        if direction:
                            send_telegram_message(
                                f"⚡ *[SINAL EXAUSTÃO - {symbol}]*\n"
                                f"📌 *Direção:* {direction}\n"
                                f"💰 *Preço:* ${price:.2f}\n"
                                f"📊 *RSI(5):* {rsi:.1f} | *BBZ:* {bbz:.2f}\n"
                                f"⏳ *Expiração:* 1 Minuto"
                            )
                            last_signal[symbol] = closed['timestamp']

            except Exception as e:
                print(f"Erro em {symbol}: {e}")
        
        time.sleep(5)

if __name__ == "__main__":
    Thread(target=keep_alive, daemon=True).start()
    run_cloud_bot()
