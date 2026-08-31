import time
import requests
import pandas as pd
from datetime import datetime

TELEGRAM_TOKEN = "8649783045:AAE2mxbkGREP3a6lrXWxh6nHaHEwfcCc5mg"
CHAT_ID = "8704308638"

SYMBOL = "ETHUSDT"
INTERVAL = "1m"
LIMIT = 200

def send_telegram_msg(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Erro ao enviar Telegram: {e}")

def fetch_data():
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval={INTERVAL}&limit={LIMIT}"
        res = requests.get(url, timeout=5).json()
        df = pd.DataFrame(res, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'c_time', 'qav', 'num_trades', 'tbv', 'tqv', 'ignore'])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        return df
    except Exception:
        return None

def calculate_indicators(df):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(7).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(7).mean()
    df['rsi7'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))

    sma20 = df['close'].rolling(20).mean()
    std20 = df['close'].rolling(20).std()
    df['bbz'] = (df['close'] - sma20) / (std20 + 1e-9)

    df['vol_rel'] = df['volume'] / df['volume'].rolling(20).mean()

    df['is_green'] = df['close'] > df['open']
    df['is_red'] = df['close'] < df['open']
    
    df['consec_green'] = (df['is_green'].astype(int).groupby((~df['is_green']).cumsum()).cumsum())
    df['consec_red'] = (df['is_red'].astype(int).groupby((~df['is_red']).cumsum()).cumsum())

    return df

def main():
    print("🚀 Bot ETH V26 Dual Rodando no Telegram...")
    last_candle_time = None

    while True:
        try:
            df = fetch_data()
            if df is not None and len(df) > 50:
                df = calculate_indicators(df)
                
                signal_candle = df.iloc[-2]
                candle_time = signal_candle['time']

                if candle_time != last_candle_time:
                    last_candle_time = candle_time
                    
                    rsi7 = round(signal_candle['rsi7'], 1)
                    bbz = round(signal_candle['bbz'], 2)
                    vol = round(signal_candle['vol_rel'], 2)
                    consec_red = int(signal_candle['consec_red'])
                    consec_green = int(signal_candle['consec_green'])
                    
                    hora_entrada = datetime.fromtimestamp((candle_time + 60000) / 1000).strftime('%H:%M:00')

                    cons_dir = None
                    if rsi7 <= 18 and bbz <= -2.2 and vol >= 1.3 and consec_red >= 3:
                        cons_dir = "CALL 🟢"
                    elif rsi7 >= 82 and bbz >= 2.2 and vol >= 1.3 and consec_green >= 3:
                        cons_dir = "PUT 🔴"

                    if cons_dir:
                        msg_cons = (
                            f"🔵 <b>[V26 CONSERVADOR] SINAL ENCONTRADO</b> 🔵\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"📊 <b>Par:</b> ETH/USDT (1M)\n"
                            f"🎯 <b>Direção:</b> {cons_dir}\n"
                            f"⏰ <b>Entrada:</b> {hora_entrada}\n"
                            f"📈 <b>RSI(7):</b> {rsi7} | <b>BBZ:</b> {bbz}\n"
                            f"📊 <b>Vol:</b> {vol}x | <b>Velas:</b> {max(consec_red, consec_green)}\n"
                            f"🛡️ <i>Perfil de Baixo Risco (Assertividade Alta)</i>"
                        )
                        send_telegram_msg(msg_cons)
                    
                    else:
                        agg_dir = None
                        if rsi7 <= 25 and bbz <= -2.0 and vol >= 1.0 and consec_red >= 2:
                            agg_dir = "CALL 🟢"
                        elif rsi7 >= 75 and bbz >= 2.0 and vol >= 1.0 and consec_green >= 2:
                            agg_dir = "PUT 🔴"

                        if agg_dir:
                            msg_agg = (
                                f"🟠 <b>[V26 AGRESSIVO] SINAL ENCONTRADO</b> 🟠\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"📊 <b>Par:</b> ETH/USDT (1M)\n"
                                f"⚡ <b>Direção:</b> {agg_dir}\n"
                                f"⏰ <b>Entrada:</b> {hora_entrada}\n"
                                f"📈 <b>RSI(7):</b> {rsi7} | <b>BBZ:</b> {bbz}\n"
                                f"📊 <b>Vol:</b> {vol}x | <b>Velas:</b> {max(consec_red, consec_green)}\n"
                                f"🔥 <i>Perfil de Alta Frequência</i>"
                            )
                            send_telegram_msg(msg_agg)

            time.sleep(3)
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    main()
