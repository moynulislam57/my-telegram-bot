import telebot
import requests
import pandas as pd
import pandas_ta as ta
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# ১. কনফিগারেশন
BOT_TOKEN = '8932222444:AAHKCUd7qEmPd3YQz_4jgiJl0ZzaRWk8LtM'
bot = telebot.TeleBot(BOT_TOKEN)
BINANCE_URL = "https://api.binance.com/api/v3/klines"

# লাইভ ডাটা আনার ফাংশন
def get_candles(symbol, interval, limit=150):
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    response = requests.get(BINANCE_URL, params=params)
    df = pd.DataFrame(response.json(), columns=[
        'Open time', 'Open', 'High', 'Low', 'Close', 'Volume',
        'Close time', 'Quote asset volume', 'Number of trades',
        'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
    ])
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        df[col] = df[col].astype(float)
    return df

# ২. ৪-ধাপের ফিল্টারিং ইঞ্জিন
def generate_ultra_signal(symbol="BTCUSDT"):
    try:
        # [ধাপ ১: মাল্টি-টাইমফ্রেম ফিল্টার] - ১ ঘণ্টার বড় ট্রেন্ড চেক করা
        df_1h = get_candles(symbol, interval="1h", limit=50)
        df_1h['EMA_50'] = ta.ema(df_1h['Close'], length=50)
        large_trend = "BULLISH" if df_1h.iloc[-1]['Close'] > df_1h.iloc[-1]['EMA_50'] else "BEARISH"
        
        # ছোট টাইমফ্রেমের ডাটা (৫ মিনিট)
        df = get_candles(symbol, interval="5m", limit=100)
        
        # ইন্ডিকেটর হিসাব
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        current_price = df.iloc[-1]['Close']
        last_closed = df.iloc[-2]
        
        # [ধাপ ২: সাপোর্ট ও রেজিস্ট্যান্স লেভেল]
        recent_data = df.iloc[-40:-2]
        resistance_level = recent_data['High'].max()
        support_level = recent_data['Low'].min()
        
        # [ধাপ ৩: ক্যান্ডেলস্টিক বডি এবং ভলিউম কনফার্মেশন]
        candle_body = abs(last_closed['Close'] - last_closed['Open'])
        avg_body = abs(df['Close'] - df['Open']).tail(20).mean()
        is_strong_candle = candle_body > avg_body # ক্যান্ডেলটি সাধারণের চেয়ে শক্তিশালী
        
        avg_volume = df['Volume'].tail(20).mean()
        is_high_volume = last_closed['Volume'] > (avg_volume * 1.25)
        
        # সিগন্যাল ইনিশিয়ালাইজেশন
        signal = "⏳ SCANNING CONSOLIDATION"
        tp, sl = 0.0, 0.0
        reason = "Market lacks institutional breakout structure."
        
        atr_value = last_closed['ATR']
        
        # [ধাপ ৪: চূড়ান্ত কনফ্লুয়েন্স লজিক]
        # বাই সিগন্যাল: বড় ট্রেন্ড আপ + রেজিস্ট্যান্স ব্রেক + স্ট্রং ক্যান্ডেল + হাই ভলিউম
        if large_trend == "BULLISH" and current_price > resistance_level and is_strong_candle and is_high_volume:
            if last_closed['RSI'] < 68:
                signal = "🚀 ULTRA-CONFIRMED BUY"
                # [ধাপ ৫: ATR ভিত্তিক রিস্ক ম্যানেজমেন্ট]
                sl = current_price - (atr_value * 1.5)
                tp = current_price + (atr_value * 3.0) # 1:2 Risk to Reward
                reason = "1H Big Trend is UP, 5M Resistance broken with an institutional size candle and high volume."
                
        # সেল সিগন্যাল: বড় ট্রেন্ড ডাউন + সাপোর্ট ব্রেক + স্ট্রং ক্যান্ডেল + হাই ভলিউম
        elif large_trend == "BEARISH" and current_price < support_level and is_strong_candle and is_high_volume:
            if last_closed['RSI'] > 32:
                signal = "💥 ULTRA-CONFIRMED SELL"
                sl = current_price + (atr_value * 1.5)
                tp = current_price - (atr_value * 3.0)
                reason = "1H Big Trend is DOWN, 5M Support broken with strong bearish pressure and heavy volume."

        return {
            "status": True, "pair": symbol, "price": current_price, "signal": signal, 
            "reason": reason, "tp": round(tp, 2), "sl": round(sl, 2), "trend": large_trend
        }
    except Exception as e:
        return {"status": False, "error": str(e)}

# ৩. টেলিগ্রাম ইন্টারফেস
def main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(KeyboardButton("💎 Scan BTC [4-Step Filter]"), KeyboardButton("💎 Scan ETH [4-Step Filter]"))
    return keyboard

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.send_message(
        message.chat.id, 
        "🛡️ **Welcome to Ultra-Confluence Algo Bot v4.0**\n\n"
        "This version filters signals through 4 mathematical layers:\n"
        "1. 1-Hour HTF Trend Filter\n"
        "2. Dynamic S/R Breakout\n"
        "3. Volume & Candle Spread Check\n"
        "4. ATR Volatility Risk Model",
        parse_mode="Markdown", reply_markup=main_menu()
    )

@bot.message_handler(func=lambda message: True)
def process_signal(message):
    chat_id = message.chat.id
    symbol = "BTCUSDT" if "BTC" in message.text else "ETHUSDT" if "ETH" in message.text else None
    
    if symbol:
        bot.send_message(chat_id, f"⚡ Running 4-Layer Quantum Analysis for {symbol}...")
        res = generate_ultra_signal(symbol)
        
        if res["status"]:
            if "SCANNING" not in res["signal"]:
                msg = (
                    f"🎯 **{res['signal']}** 🎯\n"
                    f"----------------------------------------\n"
                    f"🔸 **Asset:** {res['pair']}\n"
                    f"🔸 **HTF 1H Trend:** {res['trend']}\n"
                    f"🔸 **Execution Price:** ${res['price']}\n\n"
                    f"🟢 **Take Profit (ATR):** ${res['tp']}\n"
                    f"🔴 **Stop Loss (ATR):** ${res['sl']}\n\n"
                    f"📝 **Engine Logic:** {res['reason']}\n"
                    f"----------------------------------------\n"
                    f"⚠️ *Note: High filters mean fewer signals, but higher quality.*"
                )
            else:
                msg = (
                    f"⏳ **NO HIGH-PROBABILITY SETUP** ⏳\n"
                    f"----------------------------------------\n"
                    f"🔸 **Asset:** {res['pair']}\n"
                    f"🔸 **HTF 1H Trend:** {res['trend']}\n"
                    f"📝 **Status:** Market is filtering out low-quality noise. Waiting for institutional volume."
                )
            bot.send_message(chat_id, msg, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, f"❌ Error: {res['error']}")

if __name__ == "__main__":
    print("V4.0 Ultra Engine Running...")
bot.infinity_polling()
import telebot
import requests
import pandas as pd
import pandas_ta as ta
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# ১. কনফিগারেশন
BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN_HERE'
bot = telebot.TeleBot(BOT_TOKEN)
BINANCE_URL = "https://api.binance.com/api/v3/klines"

# লাইভ ডাটা আনার ফাংশন
def get_candles(symbol, interval, limit=150):
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    response = requests.get(BINANCE_URL, params=params)
    df = pd.DataFrame(response.json(), columns=[
        'Open time', 'Open', 'High', 'Low', 'Close', 'Volume',
        'Close time', 'Quote asset volume', 'Number of trades',
        'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
    ])
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        df[col] = df[col].astype(float)
    return df

# ২. ৪-ধাপের ফিল্টারিং ইঞ্জিন
def generate_ultra_signal(symbol="BTCUSDT"):
    try:
        # [ধাপ ১: মাল্টি-টাইমফ্রেম ফিল্টার] - ১ ঘণ্টার বড় ট্রেন্ড চেক করা
        df_1h = get_candles(symbol, interval="1h", limit=50)
        df_1h['EMA_50'] = ta.ema(df_1h['Close'], length=50)
        large_trend = "BULLISH" if df_1h.iloc[-1]['Close'] > df_1h.iloc[-1]['EMA_50'] else "BEARISH"
        
        # ছোট টাইমফ্রেমের ডাটা (৫ মিনিট)
        df = get_candles(symbol, interval="5m", limit=100)
        
        # ইন্ডিকেটর হিসাব
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        current_price = df.iloc[-1]['Close']
        last_closed = df.iloc[-2]
        
        # [ধাপ ২: সাপোর্ট ও রেজিস্ট্যান্স লেভেল]
        recent_data = df.iloc[-40:-2]
        resistance_level = recent_data['High'].max()
        support_level = recent_data['Low'].min()
        
        # [ধাপ ৩: ক্যান্ডেলস্টিক বডি এবং ভলিউম কনফার্মেশন]
        candle_body = abs(last_closed['Close'] - last_closed['Open'])
        avg_body = abs(df['Close'] - df['Open']).tail(20).mean()
        is_strong_candle = candle_body > avg_body # ক্যান্ডেলটি সাধারণের চেয়ে শক্তিশালী
        
        avg_volume = df['Volume'].tail(20).mean()
        is_high_volume = last_closed['Volume'] > (avg_volume * 1.25)
        
        # সিগন্যাল ইনিশিয়ালাইজেশন
        signal = "⏳ SCANNING CONSOLIDATION"
        tp, sl = 0.0, 0.0
        reason = "Market lacks institutional breakout structure."
        
        atr_value = last_closed['ATR']
        
        # [ধাপ ৪: চূড়ান্ত কনফ্লুয়েন্স লজিক]
        # বাই সিগন্যাল: বড় ট্রেন্ড আপ + রেজিস্ট্যান্স ব্রেক + স্ট্রং ক্যান্ডেল + হাই ভলিউম
        if large_trend == "BULLISH" and current_price > resistance_level and is_strong_candle and is_high_volume:
            if last_closed['RSI'] < 68:
                signal = "🚀 ULTRA-CONFIRMED BUY"
                # [ধাপ ৫: ATR ভিত্তিক রিস্ক ম্যানেজমেন্ট]
                sl = current_price - (atr_value * 1.5)
                tp = current_price + (atr_value * 3.0) # 1:2 Risk to Reward
                reason = "1H Big Trend is UP, 5M Resistance broken with an institutional size candle and high volume."
                
        # সেল সিগন্যাল: বড় ট্রেন্ড ডাউন + সাপোর্ট ব্রেক + স্ট্রং ক্যান্ডেল + হাই ভলিউম
        elif large_trend == "BEARISH" and current_price < support_level and is_strong_candle and is_high_volume:
            if last_closed['RSI'] > 32:
                signal = "💥 ULTRA-CONFIRMED SELL"
                sl = current_price + (atr_value * 1.5)
                tp = current_price - (atr_value * 3.0)
                reason = "1H Big Trend is DOWN, 5M Support broken with strong bearish pressure and heavy volume."

        return {
            "status": True, "pair": symbol, "price": current_price, "signal": signal, 
            "reason": reason, "tp": round(tp, 2), "sl": round(sl, 2), "trend": large_trend
        }
    except Exception as e:
        return {"status": False, "error": str(e)}

# ৩. টেলিগ্রাম ইন্টারফেস
def main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(KeyboardButton("💎 Scan BTC [4-Step Filter]"), KeyboardButton("💎 Scan ETH [4-Step Filter]"))
    return keyboard

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.send_message(
        message.chat.id, 
        "🛡️ **Welcome to Ultra-Confluence Algo Bot v4.0**\n\n"
        "This version filters signals through 4 mathematical layers:\n"
        "1. 1-Hour HTF Trend Filter\n"
        "2. Dynamic S/R Breakout\n"
        "3. Volume & Candle Spread Check\n"
        "4. ATR Volatility Risk Model",
        parse_mode="Markdown", reply_markup=main_menu()
    )

@bot.message_handler(func=lambda message: True)
def process_signal(message):
    chat_id = message.chat.id
    symbol = "BTCUSDT" if "BTC" in message.text else "ETHUSDT" if "ETH" in message.text else None
    
    if symbol:
        bot.send_message(chat_id, f"⚡ Running 4-Layer Quantum Analysis for {symbol}...")
        res = generate_ultra_signal(symbol)
        
        if res["status"]:
            if "SCANNING" not in res["signal"]:
                msg = (
                    f"🎯 **{res['signal']}** 🎯\n"
                    f"----------------------------------------\n"
                    f"🔸 **Asset:** {res['pair']}\n"
                    f"🔸 **HTF 1H Trend:** {res['trend']}\n"
                    f"🔸 **Execution Price:** ${res['price']}\n\n"
                    f"🟢 **Take Profit (ATR):** ${res['tp']}\n"
                    f"🔴 **Stop Loss (ATR):** ${res['sl']}\n\n"
                    f"📝 **Engine Logic:** {res['reason']}\n"
                    f"----------------------------------------\n"
                    f"⚠️ *Note: High filters mean fewer signals, but higher quality.*"
                )
            else:
                msg = (
                    f"⏳ **NO HIGH-PROBABILITY SETUP** ⏳\n"
                    f"----------------------------------------\n"
                    f"🔸 **Asset:** {res['pair']}\n"
                    f"🔸 **HTF 1H Trend:** {res['trend']}\n"
                    f"📝 **Status:** Market is filtering out low-quality noise. Waiting for institutional volume."
                )
            bot.send_message(chat_id, msg, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, f"❌ Error: {res['error']}")

if __name__ == "__main__":
    print("V4.0 Ultra Engine Running...")
    bot.infinity_polling()
