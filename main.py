import os
import requests
import traceback
import json
from datetime import datetime, timedelta

# ==========================================
# ⚙️ 系統設定：證交所直連狙擊
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"
SNIPER_FILE = "sniper_list.json" 

def send_msg(text):
    if not BOT_TOKEN:
        print(text)
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)

# ==========================================
# 🎯 核心濾網：法人籌碼連動
# ==========================================
def fetch_twse_data(date_str):
    """直接抓取證交所每日法人買賣超"""
    url = f"https://www.twse.com.tw/fund/T86?response=json&date={date_str}&selectType=ALL"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        if data.get('stat') == 'OK':
            return data['data']
    except:
        return None
    return None

# ==========================================
# 🚀 主邏輯：抓取近三日籌碼進行比對
# ==========================================
if __name__ == "__main__":
    try:
        # 抓取近三天的日期
        days = [(datetime.now() - timedelta(days=i)).strftime('%Y%m%d') for i in range(1, 4)]
        
        # 建立一個暫存籌碼的字典
        # 結構: {stock_id: [day1_net, day2_net, day3_net]}
        stock_history = {}
        
        for d in days:
            print(f"📡 讀取日期: {d}")
            rows = fetch_twse_data(d)
            if rows:
                for row in rows:
                    sid = row[0].strip()
                    # 處理法人淨買超 (外資 + 投信)
                    try:
                        net = int(row[4].replace(',', '')) + int(row[10].replace(',', ''))
                        if sid not in stock_history: stock_history[sid] = []
                        stock_history[sid].append(net)
                    except: continue
        
        # 狙擊目標：連續三天法人淨買超皆為正，且有增加趨勢
        targets = []
        for sid, nets in stock_history.items():
            if len(nets) == 3:
                # 條件：三天都買超 (正數)，且買超量皆 > 1000 張
                if all(n > 1000 for n in nets):
                    targets.append(sid)
        
        if targets:
            msg = f"🦞【證交所籌碼狙擊】\n🎯 鎖定籌碼連動強勢股: {', '.join(targets)}"
            with open(SNIPER_FILE, 'w', encoding='utf-8') as f:
                json.dump(targets, f)
            send_msg(msg)
        else:
            send_msg("🦞【證交所籌碼狙擊】今日無連續三日法人買超之標的。")

    except Exception as e:
        send_msg(f"⚠️ 狙擊系統崩潰: {str(e)}")
