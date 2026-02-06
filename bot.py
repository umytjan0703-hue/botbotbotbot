from telegram.ext import Updater, CommandHandler
import requests, pandas as pd, numpy as np, threading, time

TOKEN = "TELEGRAM_TOKENIN_GOY"

PAIRS = [
    "EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","NZDUSD","XAUUSD",
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT"
]

user_pair = {}
user_tf = {}
auto_users = set()

def start(update, context):
    update.message.reply_text(
        "🤖 Auto Signal Bot taýýar\n\n"
        "/pairs – pair list\n"
        "/setpair EURUSD\n"
        "/tf M1 | M2 | M5\n"
        "/signal\n"
        "/autoon | /autooff"
    )

def pairs(update, context):
    update.message.reply_text("📋 Pairlar:\n" + "\n".join(PAIRS))

def setpair(update, context):
    try:
        pair = context.args[0].upper()
        if pair in PAIRS:
            user_pair[update.effective_chat.id] = pair
            update.message.reply_text(f"✅ Pair: {pair}")
        else:
            update.message.reply_text("❌ Şeýle pair ýok")
    except:
        update.message.reply_text("/setpair EURUSD")

def set_tf(update, context):
    try:
        tf = context.args[0].upper()
        if tf in ["M1","M2","M5"]:
            user_tf[update.effective_chat.id] = tf
            update.message.reply_text(f"⏱ TF: {tf}")
        else:
            update.message.reply_text("M1 / M2 / M5")
    except:
        update.message.reply_text("/tf M1")

def get_data(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=100"
    data = requests.get(url, timeout=10).json()
    df = pd.DataFrame(data, columns=[
        "t","o","h","l","c","v","ct","q","n","tb","tq","i"
    ])
    df["c"] = df["c"].astype(float)
    return df

def indicators(df):
    df["ema9"] = df["c"].ewm(span=9).mean()
    df["ema21"] = df["c"].ewm(span=21).mean()

    delta = df["c"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    df["rsi"] = 100 - (100 / (1 + rs))

    df["mb"] = df["c"].rolling(20).mean()
    df["std"] = df["c"].rolling(20).std()
    df["bb_up"] = df["mb"] + 2 * df["std"]
    df["bb_low"] = df["mb"] - 2 * df["std"]

    ema12 = df["c"].ewm(span=12).mean()
    ema26 = df["c"].ewm(span=26).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9).mean()

    return df

def check_signal(pair):
    symbol = pair if "USDT" in pair else "BTCUSDT"
    df = indicators(get_data(symbol))
    last = df.iloc[-1]

    if (
        last.ema9 > last.ema21 and
        last.rsi < 35 and
        last.c > last.bb_low and
        last.macd > last.macd_signal
    ):
        return "🟢 BUY"

    if (
        last.ema9 < last.ema21 and
        last.rsi > 65 and
        last.c < last.bb_up and
        last.macd < last.macd_signal
    ):
        return "🔴 SELL"

    return None

def signal(update, context):
    cid = update.effective_chat.id
    pair = user_pair.get(cid, "EURUSD")
    tf = user_tf.get(cid, "M1")
    sig = check_signal(pair)
    update.message.reply_text(
        f"📊 Signal\nPair: {pair}\nTF: {tf}\nResult: {sig or 'NO SIGNAL'}"
    )

def autoon(update, context):
    auto_users.add(update.effective_chat.id)
    update.message.reply_text("✅ Auto signal ON (2 minut)")

def autooff(update, context):
    auto_users.discard(update.effective_chat.id)
    update.message.reply_text("⛔ Auto signal OFF")

def auto_loop(bot):
    while True:
        for cid in list(auto_users):
            pair = user_pair.get(cid, "EURUSD")
            tf = user_tf.get(cid, "M1")
            sig = check_signal(pair)
            if sig:
                bot.send_message(
                    cid,
                    f"🚨 AUTO SIGNAL\nPair: {pair}\nTF: {tf}\n{sig}"
                )
        time.sleep(120)  # 2 minut

updater = Updater(TOKEN)
dp = updater.dispatcher

dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("pairs", pairs))
dp.add_handler(CommandHandler("setpair", setpair))
dp.add_handler(CommandHandler("tf", set_tf))
dp.add_handler(CommandHandler("signal", signal))
dp.add_handler(CommandHandler("autoon", autoon))
dp.add_handler(CommandHandler("autooff", autooff))

threading.Thread(target=auto_loop, args=(updater.bot,), daemon=True).start()

updater.start_polling()
updater.idle()
