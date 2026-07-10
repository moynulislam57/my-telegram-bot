import telebot
import pandas as pd
import pandas_ta as ta
import yfinance as yf
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# ১. কনফিগারেশন
BOT_TOKEN = '8932222444:AAHKCUd7qEmPd3YQz_4jgiJl0ZzaRWk8LtM'
 # আপনার টোকেন বসান
bot = telebot.TeleBot(BOT_TOKEN)

# লাইভ ডাটা আনার ফাংশন
def get_binary_data(ticker):
    # ৫ মিনিটের ক্যান্ডেল ডাটা নিয়ে অ্যানালাইসিস
    data = yf.download(tickers=ticker, period="1d", interval="5m", progress=False)
    df = pd.DataFrame(data)
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    df = df.reset_index()
    return df

# ২. বাইনারি সিগন্যাল ইঞ্জিন
def generate_binary_signal(pair_name="EURUSD=X"):
    try:
        df = get_binary_data(pair_name)
        
        # ৩টি শক্তিশালী ইন্ডিকেটর ফিল্টার
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        
        # স্টোচাস্টিক অসিলেটর (Stochastic Oscillator) - বাইনারির জন্য সেরা
        stoch = ta.stoch(df['High'], df['Low'], df['Close'], k=14, d=3)
        df['STOCHk'] = stoch['STOCHk_14_3_3']
        
        current_price = float(df.iloc[-1]['Close'])
        last_closed = df.iloc[-2]
        
        rsi_val = float(last_closed['RSI'])
        ema_val = float(last_closed['EMA_20'])
        stoch_k = float(last_closed['STOCHk'])
        
        # সিগন্যাল ডিফল্ট স্ট্যাটাস
        signal_status = "HOLD"
        action = "⏳ SCANNING MARKET"
        expiry = "N/A"
        reason = "Market is sideways. No high-probability setup found."
        
        # 🟢 UP / CALL সিগন্যাল লজিক:
        # দাম EMA ২০ এর ওপরে (আপট্রেন্ড) + RSI ৪০ এর কাছাকাছি (ওভারসোল্ড থেকে রিকভারি) + স্টোচাস্টিক ২০ এর নিচে
        if current_price > ema_val and rsi_val > 40 and rsi_val < 55 and stoch_k < 25:
            signal_status = "TRADE"
            action = "🟢 UP (CALL) / ওপরে যাবে"
            expiry = "5 MINUTES (৫ মিনিট)"
            reason = "Market is in an Uptrend. Price pulled back to support and Stochastic is oversold. Strong upward momentum expected."
            
        # 🔴 DOWN / PUT সিগন্যাল লজিক:
        # দাম EMA ২০ এর নিচে (ডাউনট্রেন্ড) + RSI ৬০ এর কাছাকাছি + স্টোচাস্টিক ৮০ এর ওপরে (ওভারবট)
        elif current_price < ema_val and rsi_val < 60 and rsi_val > 45 and stoch_k > 75:
            signal_status = "TRADE"
            action = "🔴 DOWN (PUT) / নিচে যাবে"
            expiry = "5 MINUTES (৫ মিনিট)"
            reason = "Market is in a Downtrend. Price bounced to resistance and Stochastic is overbought. Strong downward momentum expected."

        return {
            "status": True,
            "signal_status": signal_status,
            "pair": pair_name.replace("=X", "").insert(3, "/"), # EURUSD থেকে EUR/USD করবে
            "price": f"{current_price:.5f}",
            "action": action,
            "expiry": expiry,
            "reason": reason
        }
    except Exception as e:
        return {"status": False, "error": str(e)}

# ৩. টেলিগ্রাম ইন্টারফেস ও বাটন
def main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(KeyboardButton("📈 EUR/USD Signal"), KeyboardButton("📈 GBP/USD Signal"))
    keyboard.row(KeyboardButton("📈 AUD/USD Signal"), KeyboardButton("📈 USD/JPY Signal"))
    return keyboard

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.send_message(
        message.chat.id, 
        "🤖 **Welcome to Binary Options Pro Signal Bot**\n\n"
        "এই বটটি সরাসরি মার্কেট ডাটা এনালাইসিস করে আপনাকে Quotex বা IQ Option এর জন্য সিগন্যাল দেবে।\n"
        "নিচের বাটনগুলো থেকে যেকোনো একটি কারেন্সি সিলেক্ট করুন:",
        parse_mode="Markdown", reply_markup=main_menu()
    )

@bot.message_handler(func=lambda message: True)
def process_signal(message):
    chat_id = message.chat.id
    
    # ইউজার কোন বাটন চাপল তা চেক করা
    pair_map = {
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "AUD/USD": "AUDUSD=X",
        "USD/JPY": "JPY=X"
    }
    
    selected_pair = None
    for key in pair_map:
        if key in message.text:
            selected_pair = pair_map[key]
            break
            
    if selected_pair:
        bot.send_message(chat_id, f"🔍 {message.text.split()[-1]} মার্কেট স্ক্যান করা হচ্ছে... দয়া করে অপেক্ষা করুন।")
        res = generate_binary_signal(selected_pair)
        
        if res["status"]:
            if res["signal_status"] == "TRADE":
                msg = (
                    f"🚨 **NEW BINARY SIGNAL IDENTIFIED** 🚨\n"
                    f"----------------------------------------\n"
                    f"💱 **Asset (কারেন্সি):** {message.text.split()[-1]}\n"
                    f"📊 **Current Price (বর্তমান মূল্য):** {res['price']}\n\n"
                    f"⚡ **ACTION (এন্ট্রি কোন দিকে):** {res['action']}\n"
                    f"⏱️ **EXPIRY TIME (ট্রেডের মেয়াদ):** {res['expiry']}\n\n"
                    f"📝 **Analysis (কারণ):** {res['reason']}\n"
                    f"----------------------------------------\n"
                    f"⚠️ *সতর্কতা: সিগন্যাল পাওয়ার সাথে সাথে পরবর্তী ৫ মিনিটের ক্যান্ডেলের জন্য এন্ট্রি নিন।*"
                )
            else:
                msg = (
                    f"⏳ **NO PERFECT SETUP YET** ⏳\n"
                    f"----------------------------------------\n"
                    f"💱 **Asset (কারেন্সি):** {message.text.split()[-1]}\n"
                    f"📊 **Current Price:** {res['price']}\n"
                    f"📝 **Status:** {res['action']}\n"
                    f"💡 *বিশ্লেষণ:* {res['reason']}"
                )
            bot.send_message(chat_id, msg, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, f"❌ ডেটা আনতে সমস্যা হয়েছে: {res['error']}")

if __name__ == "__main__":
    print("Binary Signal Bot is Live...")
    bot.infinity_polling()import telebot
import pandas as pd
import pandas_ta as ta
import yfinance as yf
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# ১. কনফিগারেশন
BOT_TOKEN = '8932222444:AAHKCUd7qEmPd3YQz_4jgiJl0ZzaRWk8LtM'
 # আপনার টোকেন বসান
bot = telebot.TeleBot(BOT_TOKEN)

# লাইভ ডাটা আনার ফাংশন
def get_binary_data(ticker):
    # ৫ মিনিটের ক্যান্ডেল ডাটা নিয়ে অ্যানালাইসিস
    data = yf.download(tickers=ticker, period="1d", interval="5m", progress=False)
    df = pd.DataFrame(data)
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    df = df.reset_index()
    return df

# ২. বাইনারি সিগন্যাল ইঞ্জিন
def generate_binary_signal(pair_name="EURUSD=X"):
    try:
        df = get_binary_data(pair_name)
        
        # ৩টি শক্তিশালী ইন্ডিকেটর ফিল্টার
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        
        # স্টোচাস্টিক অসিলেটর (Stochastic Oscillator) - বাইনারির জন্য সেরা
        stoch = ta.stoch(df['High'], df['Low'], df['Close'], k=14, d=3)
        df['STOCHk'] = stoch['STOCHk_14_3_3']
        
        current_price = float(df.iloc[-1]['Close'])
        last_closed = df.iloc[-2]
        
        rsi_val = float(last_closed['RSI'])
        ema_val = float(last_closed['EMA_20'])
        stoch_k = float(last_closed['STOCHk'])
        
        # সিগন্যাল ডিফল্ট স্ট্যাটাস
        signal_status = "HOLD"
        action = "⏳ SCANNING MARKET"
        expiry = "N/A"
        reason = "Market is sideways. No high-probability setup found."
        
        # 🟢 UP / CALL সিগন্যাল লজিক:
        # দাম EMA ২০ এর ওপরে (আপট্রেন্ড) + RSI ৪০ এর কাছাকাছি (ওভারসোল্ড থেকে রিকভারি) + স্টোচাস্টিক ২০ এর নিচে
        if current_price > ema_val and rsi_val > 40 and rsi_val < 55 and stoch_k < 25:
            signal_status = "TRADE"
            action = "🟢 UP (CALL) / ওপরে যাবে"
            expiry = "5 MINUTES (৫ মিনিট)"
            reason = "Market is in an Uptrend. Price pulled back to support and Stochastic is oversold. Strong upward momentum expected."
            
        # 🔴 DOWN / PUT সিগন্যাল লজিক:
        # দাম EMA ২০ এর নিচে (ডাউনট্রেন্ড) + RSI ৬০ এর কাছাকাছি + স্টোচাস্টিক ৮০ এর ওপরে (ওভারবট)
        elif current_price < ema_val and rsi_val < 60 and rsi_val > 45 and stoch_k > 75:
            signal_status = "TRADE"
            action = "🔴 DOWN (PUT) / নিচে যাবে"
            expiry = "5 MINUTES (৫ মিনিট)"
            reason = "Market is in a Downtrend. Price bounced to resistance and Stochastic is overbought. Strong downward momentum expected."

        return {
            "status": True,
            "signal_status": signal_status,
            "pair": pair_name.replace("=X", "").insert(3, "/"), # EURUSD থেকে EUR/USD করবে
            "price": f"{current_price:.5f}",
            "action": action,
            "expiry": expiry,
            "reason": reason
        }
    except Exception as e:
        return {"status": False, "error": str(e)}

# ৩. টেলিগ্রাম ইন্টারফেস ও বাটন
def main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(KeyboardButton("📈 EUR/USD Signal"), KeyboardButton("📈 GBP/USD Signal"))
    keyboard.row(KeyboardButton("📈 AUD/USD Signal"), KeyboardButton("📈 USD/JPY Signal"))
    return keyboard

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.send_message(
        message.chat.id, 
        "🤖 **Welcome to Binary Options Pro Signal Bot**\n\n"
        "এই বটটি সরাসরি মার্কেট ডাটা এনালাইসিস করে আপনাকে Quotex বা IQ Option এর জন্য সিগন্যাল দেবে।\n"
        "নিচের বাটনগুলো থেকে যেকোনো একটি কারেন্সি সিলেক্ট করুন:",
        parse_mode="Markdown", reply_markup=main_menu()
    )

@bot.message_handler(func=lambda message: True)
def process_signal(message):
    chat_id = message.chat.id
    
    # ইউজার কোন বাটন চাপল তা চেক করা
    pair_map = {
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "AUD/USD": "AUDUSD=X",
        "USD/JPY": "JPY=X"
    }
    
    selected_pair = None
    for key in pair_map:
        if key in message.text:
            selected_pair = pair_map[key]
            break
            
    if selected_pair:
        bot.send_message(chat_id, f"🔍 {message.text.split()[-1]} মার্কেট স্ক্যান করা হচ্ছে... দয়া করে অপেক্ষা করুন।")
        res = generate_binary_signal(selected_pair)
        
        if res["status"]:
            if res["signal_status"] == "TRADE":
                msg = (
                    f"🚨 **NEW BINARY SIGNAL IDENTIFIED** 🚨\n"
                    f"----------------------------------------\n"
                    f"💱 **Asset (কারেন্সি):** {message.text.split()[-1]}\n"
                    f"📊 **Current Price (বর্তমান মূল্য):** {res['price']}\n\n"
                    f"⚡ **ACTION (এন্ট্রি কোন দিকে):** {res['action']}\n"
                    f"⏱️ **EXPIRY TIME (ট্রেডের মেয়াদ):** {res['expiry']}\n\n"
                    f"📝 **Analysis (কারণ):** {res['reason']}\n"
                    f"----------------------------------------\n"
                    f"⚠️ *সতর্কতা: সিগন্যাল পাওয়ার সাথে সাথে পরবর্তী ৫ মিনিটের ক্যান্ডেলের জন্য এন্ট্রি নিন।*"
                )
            else:
                msg = (
                    f"⏳ **NO PERFECT SETUP YET** ⏳\n"
                    f"----------------------------------------\n"
                    f"💱 **Asset (কারেন্সি):** {message.text.split()[-1]}\n"
                    f"📊 **Current Price:** {res['price']}\n"
                    f"📝 **Status:** {res['action']}\n"
                    f"💡 *বিশ্লেষণ:* {res['reason']}"
                )
            bot.send_message(chat_id, msg, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, f"❌ ডেটা আনতে সমস্যা হয়েছে: {res['error']}")

if __name__ == "__main__":
    print("Binary Signal Bot is Live...")
    bot.infinity_polling        "2. Dynamic S/R Breakout\n"
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
