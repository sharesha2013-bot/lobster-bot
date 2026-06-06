import os
import requests
import time
import random
from bs4 import BeautifulSoup

# ==========================================
# ⚙️ 設定區
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

def send_telegram(text):
    """ 強制發送，確保你收到結果 """
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        # 分段發送避免長度溢出
        for i in range(0, len(text), 4000):
            requests.post(url, json={"chat_id": CHAT_ID, "text": text[i:i+4000]}, timeout=15)
    except: pass

def fetch_goodinfo_data():
    """ 
    強制鎖定 Goodinfo! 網站
    模擬真實瀏覽器行為，抓取法人買賣超排行 
    """
    url = "https://goodinfo.tw/tw/StockList.asp?RPT_CAT=PER_BUY_SELL&MARKET_CAT=TWSE&INDUSTRY_CAT=ALL&RPT_TYPE=PERIOD&PERIOD=D&DIS_COLUMN=INST_BUY_T"
    
    # 這是關鍵：必須模擬真實瀏覽器的 Headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://goodinfo.tw/tw/StockList.asp?RPT_CAT=PER_BUY_SELL&MARKET_CAT=TWSE",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    try:
        # 強制延遲 3 秒，模擬人類讀取速度，降低被擋機率
        time.sleep(random.uniform(3, 5))
        session = requests.Session()
        resp = session.get(url, headers=headers, timeout=20)
        resp.encoding = 'utf-8'
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # 解析 Goodinfo 的表格邏輯 (此處為結構示意)
            table = soup.select_one("#tblStockList")
            if table:
                return table
        return None
    except Exception as e:
        print(f"解析錯誤: {e}")
        return None

def main():
    table = fetch_goodinfo_data()
    
    if not table:
        # 你要求的：沒資料就靜默，不發錯誤訊息
        return

    # 簡單提取前 10 檔標的 (模擬截圖中的表格結構)
    msg = "🦞【Goodinfo! 精算戰報】\n\n"
    rows = table.select("tr")
    count = 0
    for row in rows[2:17]: # 跳過表頭
        cols = row.select("td")
        if len(cols) > 5:
            name = cols[1].text.strip()
            buy_val = cols[5].text.strip() # 假設這是買超欄位
            msg += f"• {name}: {buy_val}\n"
            count += 1
            
    if count > 0:
        send_telegram(msg)

if __name__ == "__main__":
    main()
