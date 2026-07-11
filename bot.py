import telebot
import pandas as pd
import yfinance as yf
import time

# ১. কনফিগারেশন
BOT_TOKEN = '8932222444:AAHKCUd7qEmPd3YQz_4jgiJl0ZzaRWk8LtM'
bot = telebot.TeleBot(BOT_TOKEN)

# ডাটা ফেচিং এবং ইন্ডিকেটর ইঞ্জিন
def get_analysis(ticker):
    try:
        # ৫ মিনিটের ডাটা নেওয়া
        df = yf.download(ticker, period="1d", interval="5m", progress=False)
        if df.empty: return None
        
        # ক্যালকুলেশন (বিশুদ্ধ ম্যাথ)
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands (নতুন ফিল্টার: ভলাটাইল মার্কেট চেনার জন্য)
        df['MA_20'] = df['Close'].rolling(window=20).mean()
        df['STD'] = df['Close'].rolling(window=20).std()
        df['Upper'] = df['MA_20'] + (df['STD'] * 2)
        df['Lower'] = df['MA_20'] - (df['STD'] * 2)
        
        # সর্বশেষ ক্যান্ডেল
        last = df.iloc[-1]
        
        # সিগন্যাল লজিক (ট্রিপল কনফার্মেশন)
        if last['Close'] > last['Upper'] and last['RSI'] > 70:
            return {"signal": "🔴 SELL (PUT)", "reason": "Overbought + Bollinger Breakout"}
        elif last['Close'] < last['Lower'] and last['RSI'] < 30:
            return {"signal": "🟢 BUY (CALL)", "reason": "Oversold + Bollinger Breakout"}
        else:
            return {"signal": "⏳ WAIT", "reason": "No strong trend confirmed."}
            
    except Exception as e:
        return {"error": str(e)}

# টেলিগ্রাম হ্যান্ডলার
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🤖 **Binary Algo v6.0 Active!**\n\nচুজ করুন:\n/eurusd\n/gbpusd\n/usdjpy")

@bot.message_handler(commands=['eurusd', 'gbpusd', 'usdjpy'])
def signal_handler(message):
    ticker_map = {'/eurusd': 'EURUSD=X', '/gbpusd': 'GBPUSD=X', '/usdjpy': 'JPY=X'}
    ticker = ticker_map[message.text]
    
    bot.reply_to(message, f"🔍 {message.text.upper()} স্ক্যানিং...")
    res = get_analysis(ticker)
    
    if "error" in res:
        bot.reply_to(message, "❌ ডাটা এরর। আবার চেষ্টা করুন।")
    else:
        bot.reply_to(message, f"📊 **Result:** {res['signal']}\n📝 **Reason:** {res['reason']}")

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
