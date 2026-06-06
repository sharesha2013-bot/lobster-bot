import os
import requests
import yfinance as yf
from datetime import datetime

# ==========================================
# ⚙️ 設定區
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

# 你關注的股票清單 (以 yfinance 格式)
WATCH_LIST = ["2330", "2317", "2454", "3008", "2382"] 

def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

def main():
    msg = f"🦞【龍蝦投信雷達｜{datetime.now().strftime('%m/%d')}】\n\n"
    found = False
    
    for symbol in WATCH_LIST:
        try:
            ticker = yf.Ticker(f"{symbol}.TW")
            data = ticker.history(period="1d")
            
            if not data.empty:
                price = data['Close'].iloc[-1]
                change = (data['Close'].iloc[-1] - data['Open'].iloc[0]) / data['Open'].iloc[0] * 100
                
                # 這裡是一個精算邏輯範例：
                # 判斷是否為「強勢股」(漲幅 > 2%)
                if change > 2.0:
                    msg += f"🔥 {symbol} 強勢訊號: {price:.2f} (漲幅: {change:.2f}%)\n"
                    found = True
        except:
            continue
            
    if found:
        send_telegram(msg)
    else:
        # 為了不洗版，沒符合條件時只發送簡短狀態
        send_telegram(f"🦞 雷達報告: 今日關注清單均無強勢訊號 ({datetime.now().strftime('%H:%M')})")

if __name__ == "__main__":
    main()
