import os
import requests
import time
from datetime import datetime, timedelta

# ==========================================
# ⚙️ 設定區
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

def send_telegram(text):
    """ 強制分段發送，確保訊息不被截斷 """
    for i in range(0, len(text), 4000):
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={"chat_id": CHAT_ID, "text": text[i:i+4000]}, timeout=15)
        except: pass

def fetch_data_with_backtrack():
    """ 自動回溯機制：往前回推直到找到資料 """
    for i in range(7): # 最多回溯 7 天
        target_date = datetime.now() - timedelta(days=i)
        d_str = target_date.strftime('%Y%m%d')
        url = f"https://www.twse.com.tw/r/t86?date={d_str}&selectType=ALL"
        headers = {"User-Agent": "Mozilla/5.0"}
        
        try:
            # 必須稍微延遲，模擬人類請求間隔
            time.sleep(1) 
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            # 若資料有效 (長度 > 100)
            if 'data' in data and len(data['data']) > 100:
                return data['data'], target_date.strftime('%Y-%m-%d')
        except:
            continue
    return None, None

def main():
    rows, found_date = fetch_data_with_backtrack()
    
    # 若回溯 7 天後依然沒有資料，明確回報狀態
    if not rows:
        send_telegram(f"⚠️ 龍蝦雷達執行完畢：往前回溯 7 天皆無交易資料 (可能為長假)。")
        return

    # 執行你的條件：法人合計買超 > 5000 張
    report_list = []
    for row in rows:
        try:
            sid, name = row[0].strip(), row[1].strip()
            # 4:外資, 10:投信
            fn = int(row[4].replace(',', ''))
            tn = int(row[10].replace(',', ''))
            net = fn + tn
            if net > 5000:
                report_list.append(f"• {sid} {name}: {net}張 (外:{fn}/投:{tn})")
        except: continue
        
    if report_list:
        msg = f"🦞【籌碼精算戰報｜{found_date}】\n\n🎯 強勢法人狙擊 (合計 > 5000張):\n"
        msg += "\n".join(report_list[:15])
        send_telegram(msg)
    else:
        # 如果有日期資料但沒股票符合條件，明確回報
        send_telegram(f"ℹ️ 籌碼戰報 (日期: {found_date}): 今日無股票符合法人買超 > 5000 張的條件。")

if __name__ == "__main__":
    main()
