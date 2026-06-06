import os
import requests
from datetime import datetime

# ==========================================
# ⚙️ 設定區
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        # 為了避免被 Telegram 擋掉，長訊息切割發送
        for i in range(0, len(text), 4000):
            requests.post(url, json={"chat_id": CHAT_ID, "text": text[i:i+4000]}, timeout=15)
    except: pass

def get_goodinfo_data():
    """ 
    強化版的 Goodinfo 抓取器
    加入全套 Headers 模擬真實 Chrome 瀏覽器
    """
    url = "https://goodinfo.tw/tw/StockList.asp?RPT_CAT=PER_BUY_SELL&MARKET_CAT=TWSE&INDUSTRY_CAT=ALL&RPT_TYPE=PERIOD&PERIOD=D&DIS_COLUMN=INST_BUY_T"
    
    # 這是標準瀏覽器請求頭，Goodinfo 透過檢查這些特徵來判斷是否為機器人
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://goodinfo.tw/tw/StockList.asp?RPT_CAT=PER_BUY_SELL&MARKET_CAT=TWSE",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive"
    }
    
    try:
        # 使用 Session 維持連線狀態
        session = requests.Session()
        resp = session.get(url, headers=headers, timeout=20)
        resp.encoding = 'utf-8'
        
        if resp.status_code == 200:
            # 檢查是否有內容
            if len(resp.text) > 1000: # 確保不是空的防護頁面
                return resp.text
        return None
    except Exception as e:
        print(f"抓取異常: {e}")
        return None

def main():
    html_content = get_goodinfo_data()
    
    if not html_content:
        # 這裡不發訊息，代表連 Goodinfo 都沒抓到資料
        return
    
    # 檢查內容是否真的包含關鍵數據
    if "法人買賣超" in html_content:
        send_telegram("🦞 龍蝦雷達：Goodinfo 數據源存取成功，準備開始解析。")
    else:
        # 如果網頁載入但沒關鍵字，可能是 Goodinfo 改了版面或擋住爬蟲
        send_telegram("⚠️ 警告：Goodinfo 網頁結構已改變，無法解析。")

if __name__ == "__main__":
    main()
