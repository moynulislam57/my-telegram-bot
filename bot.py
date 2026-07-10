import telebot
import pandas as pd
import yfinance as yf
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# ১. কনফিগারেশন (আপনার লাইভ টোকেন)
BOT_TOKEN = '8932222444:AAHKCUd7qEmPd3YQz_4jgiJl0ZzaRWk8LtM'  
bot = telebot.TeleBot(BOT_TOKEN)

# ডাটা আনা এবং কাস্টম গাণিতিক ইন্ডিকেটর হিসাব করা
def get_binary_signals_pure(ticker):
    try:
        # ৫ মিনিটের লাইভ ডাটা ডাউনলোড করা
        data = yf.download(tickers=ticker, period="1d", interval="5m", progress=False)
        df = pd.DataFrame(data)
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
        df = df.reset_index()
        
        # ক) EMA 20 এর হিসাব
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        
        # খ) RSI 14 এর হিসাব (পিউর ম্যাথ)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # গ) Stochastic Oscillator (%K) এর হিসাব
        low_14 = df['Low'].rolling(window=14).min()
        high_14 = df['High'].rolling(window=14).max()
        df['STOCHk'] = 100 * ((df['Close'] - low_14) / (high_14 - low_14))
        
        # সর্বশেষ সম্পন্ন হওয়া ক্যান্ডেলের ডাটা নেওয়া
        current_price = float(df.iloc[-1]['Close'])
        last_closed = df.iloc[-2]
        
        rsi_val = float(last_closed['RSI'])
        ema_val = float(last_closed['EMA_20'])
        stoch_k = float(last_closed['STOCHk'])
        
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

        clean_name = ticker.replace("=X", "")
        display_name = f"{clean_name[:3]}/{clean_name[3:]}" if len(clean_name) == 6 else clean_name

        return {
            "status": True, "signal_status": signal_status, "pair": display_name,
            "price": f"{current_price:.5f}", "action": action, "expiry": expiry, "reason": reason
        }
    except Exception as e:
        return {"status": False, "error": str(e)}

# ২. টেলিগ্রাম ইন্টারফেস ও বাটন
def main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(KeyboardButton("📈 EUR/USD Signal"), KeyboardButton("📈 GBP/USD Signal"))
    keyboard.row(KeyboardButton("📈 AUD/USD Signal"), KeyboardButton("📈 USD/JPY Signal"))
    return keyboard

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.send_message(
        message.chat.id, 
        "🤖 **Welcome to Binary Options Pro Signal Bot v5.5**\n\n"
        "এই বটটি সরাসরি মার্কেট ডাটা এনালাইসিস করে আপনাকে Quotex বা IQ Option এর জন্য সিগন্যাল দেবে।\n"
        "নিচের বাটনগুলো থেকে যেকোনো একটি কারেন্সি সিলেক্ট করুন:",
        parse_mode="Markdown", reply_markup=main_menu()
    )

@bot.message_handler(func=lambda message: True)
def process_signal(message):
    chat_id = message.chat.id
    
    pair_map = {
        "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X",
        "AUD/USD": "AUDUSD=X", "USD/JPY": "JPY=X"
    }
    
    selected_pair = None
    for key in pair_map:
        if key in message.text:
            selected_pair = pair_map[key]
            break
            
    if selected_pair:
        bot.send_message(chat_id, f"🔍 {message.text.split()[-1]} মার্কেট স্ক্যান করা হচ্ছে... দয়া করে অপেক্ষা করুন।")
        res = get_binary_signals_pure(selected_pair)
        
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
    print("Pure Math Binary Engine is Running Without Errors...")
    bot.infinity_polling()
