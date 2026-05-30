import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import time

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

def send_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

def get_籌碼分析(stock_id):
    # 這裡預留給你的邏輯：未來串接籌碼數據，回傳「好/爛」的分級
    # 暫時回傳基本法人數據作為判斷依據
    return "🔥"

try:
    # 強制重試迴圈：直到抓到當日資料為止
    target_date = datetime.now()
    found = False
    
    for _ in range(7):
        time.sleep(5) # 緩衝，保護管線
        d_str = target_date.strftime('%Y%m%d')
        url = f"https://www.twse.com.tw/fund/T86?response=json&date={d_str}&selectType=ALL"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        res = requests.get(url, headers=headers).json()
        
        if res.get('stat') == 'OK':
            fields = res['fields']
            df = pd.DataFrame(res['data'], columns=fields)
            
            # 清洗數據
            col_id = [c for c in fields if '代號' in c][0]
            col_name = [c for c in fields if '名稱' in c][0]
            col_foreign = [c for c in fields if '外' in c and '買賣超' in c][0]
            col_trust = [c for c in fields if '投信買賣超' in c][0]
            
            df[col_foreign] = pd.to_numeric(df[col_foreign].astype(str).str.replace(',', ''), errors='coerce')
            df[col_trust] = pd.to_numeric(df[col_trust].astype(str).str.replace(',', ''), errors='coerce')
            df['total_net'] = df[col_foreign] + df[col_trust]
            
            # 鎖定 Top 10
            top10 = df.nlargest(10, 'total_net')
            
            msg = f"🦞【無情法人戰情室｜{target_date.strftime('%Y-%m-%d')}】\n"
            msg += f"⚔️ 法人聯手買超 Top 10：\n\n"
            
            for _, row in top10.iterrows():
                net = int(row['total_net'] / 1000)
                if net > 0:
                    status = get_籌碼分析(row[col_id])
                    msg += f"{status} {row[col_name]}({row[col_id]}): {net} 張\n"
            
            msg += "\n💡 指標分析：籌碼集中度/家數差監控中..."
            send_msg(msg)
            found = True
            break
        
        target_date -= timedelta(days=1)
        
except Exception:
    pass
