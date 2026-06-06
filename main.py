import requests
import json
from datetime import datetime, timedelta

def get_投信買超():
    # 設定狙擊範圍：過去 15 個交易日
    days_to_check = 15
    tracker = {}
    
    current_date = datetime.now()
    checked_days = 0
    
    # 只要抓到 15 個有交易的日子就停
    while checked_days < days_to_check:
        d_str = current_date.strftime('%Y%m%d')
        url = f"https://www.twse.com.tw/fund/T86?response=json&date={d_str}&selectType=ALL"
        
        try:
            res = requests.get(url, timeout=10)
            data = res.json()
            if data.get('stat') == 'OK':
                checked_days += 1
                for row in data['data']:
                    sid = row[0].strip()
                    # 投信淨買超在欄位 10
                    try:
                        buy = int(row[10].replace(',', ''))
                        tracker[sid] = tracker.get(sid, 0) + buy
                    except: continue
        except: pass
        current_date -= timedelta(days=1)
        
    # 篩選：15天累計買超 > 1000 張 (因為證交所單位是股，所以是 1,000,000)
    targets = [sid for sid, total in tracker.items() if total >= 1000000]
    return targets

if __name__ == "__main__":
    targets = get_投信買超()
    print(f"🦞 狙擊名單: {', '.join(targets)}")
    # 存檔供您後續比對
    with open("sniper_list.json", "w") as f:
        json.dump(targets, f)
