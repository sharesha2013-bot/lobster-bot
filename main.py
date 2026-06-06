import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ==========================================
# ⚙️ 設定區
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=15)
    except: pass

def get_goodinfo_data():
    """ 
    強制抓取 Goodinfo! 法人買賣超排行
    """
    url = "https://goodinfo.tw/tw/StockList.asp?RPT_CAT=PER_BUY_SELL&MARKET_CAT=TWSE&INDUSTRY_CAT=ALL&RPT_TYPE=PERIOD&PERIOD=D&DIS_COLUMN=INST_BUY_T"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'utf-8' # Goodinfo 是 Big5 或 utf-8，指定編碼
        if resp.status_code == 200:
            return resp.text
    except Exception as e:
        print(f"抓取失敗: {e}")
    return None

def main():
    html_content = get_goodinfo_data()
    
    if not html_content:
        # 這裡不發送訊息，保持靜默，因為可能是網路波動
        return
    
    # 簡單測試解析：檢查網頁是否成功讀取到「法人買賣超」關鍵字
    if "法人買賣超" in html_content:
        send_telegram("🦞 龍蝦雷達：已成功存取 Goodinfo! 籌碼資料源。")
        # 下一步：這裡我們會用 BeautifulSoup 解析具體的「投本比」數據
    else:
        send_telegram("⚠️ 警告：無法解析 Goodinfo! 網頁內容。")

if __name__ == "__main__":
    main()
