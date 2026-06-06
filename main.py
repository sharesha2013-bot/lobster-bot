import requests
from datetime import datetime, timedelta

# ==========================================
# 核心戰法：自動回溯搜索機制
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

def send_telegram(text):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                      json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except: pass

def fetch_data_with_backtrack():
    """ 自動向前回溯日期，直到找到最近的交易資料為止 """
    for i in range(7): # 最多回推 7 天
        d = datetime.now() - timedelta(days=i)
        d_str = d.strftime('%Y%m%d')
        url = f"https://www.twse.com.tw/r/t86?date={d_str}&selectType=ALL"
        headers = {"User-Agent": "Mozilla/5.0"}
        
        try:
            resp = requests.get(url, headers=headers, timeout=8)
            data = resp.json()
            # 若資料長度大於 100，代表是有效的交易日資料
            if 'data' in data and len(data['data']) > 100:
                return data['data'], d.strftime('%m/%d')
        except: continue
    return None, None

def main():
    rows, found_date = fetch_data_with_backtrack()
    
    # 只要沒找到資料就靜默退出，不發任何錯誤訊息
    if not rows:
        return

    # 執行條件：法人合計買超 > 5000 張
    report_list = []
    for row in rows:
        try:
            sid, name = row[0].strip(), row[1].strip()
            fn, tn = int(row[4].replace(',', '')), int(row[10].replace(',', ''))
            net = fn + tn
            if net > 5000:
                report_list.append(f"{sid} {name}: {net}張 (外:{fn}/投:{tn})")
        except: continue
        
    if report_list:
        msg = f"🦞【籌碼精算戰報｜{found_date}】\n\n🎯 強勢法人狙擊:\n"
        msg += "\n".join(report_list[:15])
        send_telegram(msg)

if __name__ == "__main__":
    main()
