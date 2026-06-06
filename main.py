import os
import requests
from bs4 import BeautifulSoup

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
    最終強化版抓取器：模擬完整瀏覽器環境
    """
    url = "https://goodinfo.tw/tw/StockList.asp?RPT_CAT=PER_BUY_SELL&MARKET_CAT=TWSE&INDUSTRY_CAT=ALL&RPT_TYPE=PERIOD&PERIOD=D&DIS_COLUMN=INST_BUY_T"
    
    # 增加更多偽裝特徵，繞過網站檢測
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Referer": "https://goodinfo.tw/",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0"
    }
    
    try:
        # 增加一個 session
        session = requests.Session()
        resp = session.get(url, headers=headers, timeout=20)
        
        # 狀態碼檢查
        if resp.status_code == 200:
            return resp.text
        else:
            return f"HTTP_ERROR_{resp.status_code}"
            
    except Exception as e:
        return f"CONN_ERROR_{str(e)}"

def main():
    result = get_goodinfo_data()
    
    # 如果結果是錯誤代碼，我們明確發送給 Telegram
    if result.startswith("HTTP_") or result.startswith("CONN_"):
        send_telegram(f"❌ Goodinfo 存取失敗: {result}")
        return
        
    # 如果順利拿到網頁
    soup = BeautifulSoup(result, 'html.parser')
    
    # 檢查是否有內容
    if "法人買賣超" in result:
        send_telegram("✅ Goodinfo 存取成功！資料已在手上，隨時可進行解析。")
    else:
        # 如果拿到網頁但沒內容，代表觸發了驗證碼頁面
        send_telegram("⚠️ 警告：Goodinfo 觸發了防爬蟲驗證，目前無法解析。")

if __name__ == "__main__":
    main()
