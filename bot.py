import telebot
import pandas as pd
import pandas_ta as ta
import yfinance as yf
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# ১. কনফিগারেশন (আপনার দেওয়া লাইভ টোকেন বসানো হয়েছে)
BOT_TOKEN = '8932222444:AAHKCUd7qEmPd3YQz_4jgiJl0ZzaRWk8LtM'  
bot = telebot.TeleBot(BOT_TOKEN)

# লাইভ ডাটা আনার ফাংশน
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
        
        # স্টোচাস্টিক অসিলেটর (Stochastic Oscillator)
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
        
        # 🟢 UP / CALL সিগন্যাল লজিক
        if current_price > ema_val and rsi_val > 40 and rsi_val < 55 and stoch_k < 25:
            signal_status = "TRADE"
            action = "🟢 UP (CALL) / ওপরে যাবে"
            expiry = "5 MINUTES (৫ মিনিট)"
            reason = "Market is in an Uptrend. Price pulled back to support and Stochastic is oversold. Strong upward momentum expected."
            
        # 🔴 DOWN / PUT সিগন্যাল লজিক
        elif current_price < ema_val and rsi_val < 60 and rsi_val > 45 and stoch_k > 75:
            signal_status = "TRADE"
            action = "🔴 DOWN (PUT) / নিচে যাবে"
            expiry = "5 MINUTES (৫ মিনিট)"
            reason = "Market is in a Downtrend. Price bounced to resistance and Stochastic is overbought. Strong downward momentum expected."

        # কারেন্সি নাম ফরম্যাট করার সঠিক কোড (টাইপো ফিক্সড)
        clean_name = pair_name.replace("=X", "")
        if len(clean_name) == 6:
            display_name = f"{clean_name[:3]}/{clean_name[3:]}"
        else:
            display_name = clean_name

        return {
            "status": True,
            "signal_status": signal_status,
            "pair": display_name,
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
                    f"💱 **Asset (কারেন্সি):** {res['pair']}\n"
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
                    f"💱 **Asset (কারেন্সি):** {res['pair']}\n"
                    f"📊 **Current Price:** {res['price']}\n"
                    f"📝 **Status:** {res['action']}\n"
                    f"💡 *বিশ্লেষণ:* {res['reason']}"
                )
            bot.send_message(chat_id, msg, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, f"❌ ডেটা আনতে সমস্যা হয়েছে: {res['error']}")

if __name__ == "__main__":
    print("Binary Signal Bot is Live and Running...")
    bot.infinity_polling()
