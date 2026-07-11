import telebot
import pandas as pd
import yfinance as yf

# ১. কনফিগারেশন
BOT_TOKEN = '8932222444:AAHKCUd7qEmPd3YQz_4jgiJl0ZzaRWk8LtM'
bot = telebot.TeleBot(BOT_TOKEN)

# ডাটা ফেচিং এবং ইন্ডিকেটর ইঞ্জিন
def get_analysis(ticker):
    try:
        # ৫ মিনিটের ডাটা নেওয়া (গ্রুপ ডাটা হ্যান্ডলিং ফিক্স করা হয়েছে)
        df = yf.download(ticker, period="1d", interval="5m", progress=False, group_by='ticker')
        
        if df.empty: 
            return {"error": "মার্কেট ডাটা খালি বা পাওয়া যায়নি।"}
            
        # মাল্টি-ইনডেক্স কলাম ফিক্স করার জন্য সেফটি কোড
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(1)
            
        # ইনডেক্স ঠিক করা এবং ক্লোজ প্রাইসকে ফ্লোট-এ কনভার্ট করা
        df = df.reset_index()
        df['Close'] = df['Close'].astype(float)
        df['High'] = df['High'].astype(float)
        df['Low'] = df['Low'].astype(float)
        
        # ক্যালকুলেশন (বিশুদ্ধ ম্যাথ)
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        
        # RSI ক্যালকুলেশন
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands (ভলাটাইল মার্কেট ফিল্টার)
        df['MA_20'] = df['Close'].rolling(window=20).mean()
        df['STD'] = df['Close'].rolling(window=20).std()
        df['Upper'] = df['MA_20'] + (df['STD'] * 2)
        df['Lower'] = df['MA_20'] - (df['STD'] * 2)
        
        # সর্বশেষ সম্পন্ন হওয়া ক্যান্ডেল (ইন্ডেক্স -২)
        last = df.iloc[-2]
        current_price = float(df.iloc[-1]['Close'])
        
        # সিগন্যাল লজিক
        if current_price > last['Upper'] and last['RSI'] > 65:
            return {
                "signal": "🔴 DOWN (PUT) / নিচে যাবে", 
                "reason": f"Market Overbought (RSI: {last['RSI']:.1f}) + Upper Bollinger Band Breakout.",
                "price": f"{current_price:.5f}"
            }
        elif current_price < last['Lower'] and last['RSI'] < 35:
            return {
                "signal": "🟢 UP (CALL) / ওপরে যাবে", 
                "reason": f"Market Oversold (RSI: {last['RSI']:.1f}) + Lower Bollinger Band Breakout.",
                "price": f"{current_price:.5f}"
            }
        else:
            return {
                "signal": "⏳ WAIT / অপেক্ষা করুন", 
                "reason": "কোনো শক্তিশালী ব্রেকআউট বা ট্রেন্ড কনফার্ম হয়নি।",
                "price": f"{current_price:.5f}"
            }
            
    except Exception as e:
        return {"error": str(e)}

# ২. টেলিগ্রাম হ্যান্ডলার
@bot.message_handler(commands=['start'])
def start(message):
    welcome_msg = (
        "🤖 **Binary Options Pro Bot v6.5**\n\n"
        "লাইভ কারেন্সি সিগন্যাল পেতে নিচের যেকোনো একটি কমান্ডে ক্লিক করুন:\n\n"
        "📊 /eurusd - EUR/USD স্ক্যান করুন\n"
        "📊 /gbpusd - GBP/USD স্ক্যান করুন\n"
        "📊 /usdjpy - USD/JPY স্ক্যান করুন"
    )
    bot.send_message(message.chat.id, welcome_msg, parse_mode="Markdown")

@bot.message_handler(commands=['eurusd', 'gbpusd', 'usdjpy'])
def signal_handler(message):
    ticker_map = {'/eurusd': 'EURUSD=X', '/gbpusd': 'GBPUSD=X', '/usdjpy': 'JPY=X'}
    ticker = ticker_map[message.text]
    pair_name = message.text.replace("/", "").upper()
    
    bot.send_message(message.chat.id, f"🔍 {pair_name} লাইভ মার্কেট স্ক্যান করা হচ্ছে...")
    res = get_analysis(ticker)
    
    if "error" in res:
        bot.send_message(message.chat.id, f"❌ **ডাটা এরর:** {res['error']}\n\n*পরামর্শ: উইকএন্ডে (শনিবার ও রবিবার) ফরেক্স মার্কেট বন্ধ থাকে, তাই এই এরর আসতে পারে। সোমবার থেকে শুক্রবার ট্রাই করুন।*", parse_mode="Markdown")
    else:
        msg = (
            f"🎯 **BINARY SIGNAL OUTCOME** 🎯\n"
            f"-------------------------------------\n"
            f"💱 **Asset:** {pair_name}\n"
            f"📊 **Live Price:** {res['price']}\n\n"
            f"⚡ **Action:** {res['signal']}\n"
            f"📝 **Reason:** {res['reason']}\n"
            f"-------------------------------------\n"
            f"⚠️ *মেয়াদ: ৫ মিনিটের ট্রেডের জন্য এটি কার্যকর।*"
        )
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")

if __name__ == "__main__":
    print("V6.5 Data Engine is Running...")
    bot.infinity_polling()
