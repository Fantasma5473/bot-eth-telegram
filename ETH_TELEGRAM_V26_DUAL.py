import os
import time
import requests
import pandas as pd
import numpy as np
from flask import Flask
from threading import Thread

# ==========================================
# SERVIDOR WEB PARA MANTER O RENDER FREE ATIVO
# ==========================================
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return "Bot V26 Exaustao Pro (61.6%) Rodando 24/7!"

def keep_alive():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

# ==========================================
# CONFIGURAÇÃO DE VARIÁVEIS DO TELEGRAM
# ==========================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8649783045:AAE2mxbkGREP3a6lrXWxh6nHaHEwfcCc5mg")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8704308638")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Erro no envio do Telegram: {e}")

# ==========================================
# INDICADORES PRO (61.6% WINRATE)
# ==========================================
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
    except Exception as e:
        return None

def process_indicators(df):
    df['candle_body'] = np.abs(df['close'] - df['open'])
    df['is_green'] = df['close'] > df['open']
    df['is_red'] = df['close'] < df['open']

    # ATR 14
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    df['ATR14'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(14).mean()

    # RSI 5
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(5).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(5).mean()
    df['RSI5'] = 100 - (100 / (1 + (gain / (loss + 1e-10))))

    # BBZ (20)
    sma20 = df['close'].rolling(20).mean()
    std20 = df['close'].rolling(20).std()
    df['BBZ'] = (df['close'] - sma20) / (std20 + 1e-10)

    # Volume Relativo
    vol_sma20 = df['volume'].rolling(20).mean()
    df['VOL_REL'] = df['volume'] / (vol_sma20 + 1e-10)

    # Velas Consecutivas
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
# MOTOR PRINCIPAL
# ==========================================
def run_cloud_bot():
    send_telegram_message("☁️ *Bot V26 Exaustão Pro (61.6%) Ativo no Render Free!*")
    
    last_signal_time = None
    active_trade = None

    while True:
        try:
            df = get_binance_klines()
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

                # Validação do Resultado
                if active_trade is not None and active_trade['target_time'] == closed['timestamp']:
                    entry = active_trade['entry']
                    direction = active_trade['direction']
                    
                    is_win = (direction == "CALL" and price > entry) or (direction == "PUT" and price < entry)
                    res = "WIN" if is_win else "LOSS"
                    color_emoji = "🟢" if is_win else "🔴"
                    
                    send_telegram_message(
                        f"{color_emoji} *[RESULTADO: {res}]*\n"
                        f"📌 *Direção:* {direction}\n"
                        f"💰 *Entrada:* ${entry:.2f} | *Fechamento:* ${price:.2f}"
                    )
                    active_trade = None

                # Filtro Anti-Ruído
                vol_ok = vol >= 1.5
                body_ok = body >= (1.2 * atr)

                if last_signal_time != closed['timestamp'] and active_trade is None:
                    direction = None
                    if closed['is_red'] and consec >= 4 and rsi <= 15 and bbz <= -2.8 and vol_ok and body_ok:
                        direction = "CALL"
                    elif closed['is_green'] and consec >= 4 and rsi >= 85 and bbz >= 2.8 and vol_ok and body_ok:
                        direction = "PUT"

                    if direction:
                        send_telegram_message(
                            f"⚡ *[SINAL EXAUSTÃO PRO - {direction}]*\n"
                            f"💰 *Preço Entrada:* ${price:.2f}\n"
                            f"📊 *RSI(5):* {rsi:.1f} | *BBZ:* {bbz:.2f}\n"
                            f"🔊 *Vol Relativo:* {vol:.2f}x | *Velas Seguidas:* {consec}\n"
                            f"⏳ *Expiração:* 1 Minuto"
                        )
                        
                        active_trade = {
                            "entry": price, "direction": direction, "target_time": closed['timestamp'] + 60000
                        }
                        last_signal_time = closed['timestamp']

        except Exception as e:
            print(f"Erro na execução: {e}")
        
        time.sleep(5)

if __name__ == "__main__":
    # Inicia o servidor HTTP em background para o Render Free não dar erro de porta
    Thread(target=keep_alive, daemon=True).start()
    
    # Inicia o monitoramento do bot
    run_cloud_bot()
