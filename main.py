import os
import requests
import time
import random
from datetime import datetime

# ==========================================
# ⚙️ 設定區
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

# 模擬真實瀏覽器指紋 (防鎖關鍵)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Referer": "https://www.twse.com.tw/zh/trading/foreign/t86.html"
}

def send_telegram(text):
    """ 強制分段發送，防止 Telegram API 截斷 """
    for i in range(0, len(text), 4000):
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={"chat_id": CHAT_ID, "text": text[i:i+4000]}, timeout=15)
        except: pass

def fetch_data():
    """ 
    最簡架構：僅抓取當日資料
    若當日無資料 (如週末)，直接返回 None 並靜默，不再拋錯
    """
    d_str = datetime.now().strftime('%Y%m%d')
    url = f"https://www.twse.com.tw/r/t86?date={d_str}&selectType=ALL"
    
    try:
        # 強制延遲 1-2 秒模擬人類行為
        time.sleep(random.uniform(1, 2))
        response = requests.get(url, headers=HEADERS, timeout=20)
        data = response.json()
        
        # 檢查是否有資料 (長度超過 100 確保不是空表)
        if 'data' in data and len(data['data']) > 100:
            return data['data'], d_str
    except:
        pass # 失敗即靜默
    return None, None

def main():
    rows, d_str = fetch_data()
    
    # 若無資料，系統安靜退出，不再發送「雷達警告」
    if not rows:
        return

    # 籌碼精算戰法：法人合計買超 > 5000 張
    report_list = []
    for row in rows:
        try:
            sid, name = row[0].strip(), row[1].strip()
            # 欄位：4 外資合計, 10 投信合計
            fn = int(row[4].replace(',', ''))
            tn = int(row[10].replace(',', ''))
            net = fn + tn
            
            if net > 5000:
                report_list.append(f"• {sid} {name}: {net}張 (外:{fn}/投:{tn})")
        except: continue
        
    if report_list:
        msg = f"🦞【籌碼精算戰報｜{d_str}】\n\n🎯 強勢狙擊 (法人合計買超 > 5000張):\n"
        msg += "\n".join(report_list[:15])
        send_telegram(msg)

if __name__ == "__main__":
    main()
