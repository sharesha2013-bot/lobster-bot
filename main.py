import yfinance as yf
import os
import requests
from datetime import datetime

# 設定 Telegram 發送
def send_telegram(text):
    bot_token = os.getenv('BOT_TOKEN')
    chat_id = "8543567603"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

def check_stock_data(ticker_symbol):
    """
    使用 yfinance 抓取股票資料
    這裡以台積電 (2330.TW) 為例
    """
    # yfinance 台股代號需要加上 .TW
    ticker = yf.Ticker(f"{ticker_symbol}.TW")
    
    # 獲取財務與籌碼相關資訊
    info = ticker.info
    
    # 你可以在這裡篩選，例如：查看外資持股比例 (institutionalHolders)
    # yfinance 會自動處理連線，不會被封鎖
    return info

def main():
    # 測試：抓取台積電數據
    try:
        data = check_stock_data("2330")
        name = data.get('longName', '未知')
        # 測試發送
        send_telegram(f"✅ yfinance 連線成功！\n目標: {name}\n資料抓取正常。")
    except Exception as e:
        send_telegram(f"❌ yfinance 錯誤: {e}")

if __name__ == "__main__":
    main()
