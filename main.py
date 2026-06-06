import requests
import os
from datetime import datetime

# ==========================================
# 核心設定
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

def send_telegram(text):
    """ 強制發送，失敗不拋錯，保持系統靜默 """
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except: pass

def fetch_data():
    """ 強制鎖定證交所法人統計頁面，不進行任何日期回溯 """
    # 直接使用今日日期，沒有就沒有
    d_str = datetime.now().strftime('%Y%m%d')
    url = f"https://www.twse.com.tw/r/t86?date={d_str}&selectType=ALL"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.twse.com.tw/zh/trading/foreign/t86.html"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        if 'data' in data: return data['data']
    except:
        return None
    return None

def main():
    rows = fetch_data()
    
    # 邏輯：若無資料，直接退出，絕不報錯
    if not rows:
        return

    # 執行條件一：法人合計買超 > 5000 張
    report_list = []
    for row in rows:
        try:
            # 欄位解析：0:代號, 1:名稱, 4:外資合計買賣超, 10:投信合計買賣超
            sid, name = row[0].strip(), row[1].strip()
            fn, tn = int(row[4].replace(',', '')), int(row[10].replace(',', ''))
            net = fn + tn
            
            if net > 5000:
                report_list.append(f"{sid} {name}: {net}張 (外:{fn}/投:{tn})")
        except: continue
        
    if report_list:
        msg = f"🦞【法人精算戰報｜{datetime.now().strftime('%m/%d')}】\n\n"
        msg += "🎯 強勢狙擊 (法人合計買超 > 5000張):\n"
        msg += "\n".join(report_list[:15])
        send_telegram(msg)

if __name__ == "__main__":
    main()
