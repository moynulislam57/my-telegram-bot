import telebot
import pandas as pd
import yfinance as yf
import time
import threading
from datetime import datetime, timezone, timedelta

# ১. কনফিগারেশন
BOT_TOKEN = '8932222444:AAHKCUd7qEmPd3YQz_4jgiJl0ZzaRWk8LtM'
bot = telebot.TeleBot(BOT_TOKEN)

active_users = set()
bd_tz = timezone(timedelta(hours=6))

# ২. ১-মিনিট Quotex অ্যালগরিদম ইঞ্জিন
def get_1m_quotex_analysis(ticker):
    try:
        # ১ মিনিটের ক্যান্ডেল ডাটা নিয়ে আসা
        df = yf.download(ticker, period="1d", interval="1m", progress=False)
        if df.empty: return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df.reset_index()
        df['Close'] = df['Close'].astype(float)
        
        # RSI ক্যালকুলেশন
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands (ভলাটাইল ব্রেকআউট ট্র্যাক করার জন্য)
        df['MA_20'] = df['Close'].rolling(window=20).mean()
        df['STD'] = df['Close'].rolling(window=20).std()
        df['Upper'] = df['MA_20'] + (df['STD'] * 2)
        df['Lower'] = df['MA_20'] - (df['STD'] * 2)
        
        last = df.iloc[-2]
        current_price = float(df.iloc[-1]['Close'])
        
        # ⚡ Quotex 1-Min Scalping Strategy
        if current_price > last['Upper'] and last['RSI'] > 70:
            return {"direction": "🔴 DOWN (PUT) / SELL", "price": f"{current_price:.5f}"}
        elif current_price < last['Lower'] and last['RSI'] < 30:
            return {"direction": "🟢 UP (CALL) / BUY", "price": f"{current_price:.5f}"}
        
        return None
            
    except Exception as e:
        return None

# ৩. ব্যাকগ্রাউন্ড অটো স্ক্যানার লুপ (প্রতি মিনিটে চেক করবে)
def auto_quotex_scanner():
    quotex_assets = {'EURUSD=X': 'EUR/USD', 'GBPUSD=X': 'GBP/USD', 'JPY=X': 'USD/JPY'}
    
    while True:
        now_bd = datetime.now(bd_tz)
        
        # প্রতি মিনিটের ৫২ তম সেকেন্ডে স্ক্যান করবে (ট্রেডার যাতে ৮ সেকেন্ড সময় পায়)
        if now_bd.second == 52:
            if not active_users:
                time.sleep(1)
                continue
            
            # ঠিক পরবর্তী ক্যান্ডেল শুরুর সময় (Quotex Entry Time)
            entry_time = (now_bd + timedelta(minutes=1)).strftime("%H:%M:00")
            
            for ticker, asset_name in quotex_assets.items():
                res = get_1m_quotex_analysis(ticker)
                
                if res:
                    msg = (
                        f"🎯 **QUOTEX LIVE ALGO SIGNAL** 🎯\n"
                        f"-------------------------------------\n"
                        f"💱 **Asset Name:** {asset_name}\n"
                        f"📊 **Strike Price:** {res['price']}\n\n"
                        f"⚡ **Direction (ইনভেস্ট):** {res['direction']}\n"
                        f"⏱️ **Quotex Entry Time:** ঠিক **{entry_time}** সেকেন্ডে ক্লিক!\n"
                        f"⏳ **Timeframe / Expiry:** 1 MINUTE (১ মিনিট)\n"
                        f"-------------------------------------\n"
                        f"⚠️ *Quotex টিপস: আপনার ফোনের/পিসির ঘড়ির সেকেন্ড যখনই ০০ হবে, সাথে সাথে ক্লিক করবেন। এক সেকেন্ডও দেরি করা যাবে না।* 🚀"
                    )
                    
                    for user_id in list(active_users):
                        try:
                            bot.send_message(user_id, msg, parse_mode="Markdown")
                        except Exception as e:
                            print(f"Error: {e}")
            
            # সিগন্যাল পাঠানো শেষ হলে একটু পজ নিবে যাতে লুপ রিপিট না হয়
            time.sleep(2)
        else:
            time.sleep(1)

# ৪. টেলিগ্রাম কমান্ড হ্যান্ডলার
@bot.message_handler(commands=['start'])
def start_bot(message):
    active_users.add(message.chat.id)
    welcome_text = (
        "🟢 **Quotex Auto-Trading Signal Engine v8.0 Active**\n\n"
        "আপনার অ্যাকাউন্টটি সফলভাবে লাইভ সিগন্যাল ইঞ্জিনের সাথে কানেক্ট হয়েছে।\n"
        "বট এখন ব্যাকগ্রাউন্ডে **EUR/USD, GBP/USD, USD/JPY** এর ১ মিনিটের ক্যান্ডেল স্ক্যান করছে।\n\n"
        "💡 মার্কেট পারফেক্ট পজিশনে আসলেই আপনার কাছে Quotex ফরম্যাটে এন্ট্রি টাইম সহ মেসেজ চলে আসবে।\n\n"
        "🛑 সিগন্যাল রিসিভ করা বন্ধ করতে চাইলে চাপুন: /stop"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['stop'])
def stop_bot(message):
    if message.chat.id in active_users:
        active_users.remove(message.chat.id)
    bot.send_message(message.chat.id, "🛑 **Quotex অটো সিগন্যাল ইঞ্জিন বন্ধ করা হয়েছে।**\nআবার চালু করতে /start চাপুন।", parse_mode="Markdown")

if __name__ == "__main__":
    print("Quotex Live 1-Min System is Online...")
    threading.Thread(target=auto_quotex_scanner, daemon=True).start()
    bot.infinity_polling()
