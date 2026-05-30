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

try:
    # 🕒 休息 5 秒，假裝是真人，避開證交所防護
    time.sleep(5)
    
    target_date = datetime.now()
    d_str = target_date.strftime('%Y%m%d')
    
    # 🎯 直打證交所官方每日結算網頁
    url = f"https://www.twse.com.tw/fund/T86?response=json&date={d_str}&selectType=ALL"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    res = requests.get(url, headers=headers).json()
    
    if res.get('stat') == 'OK':
        fields = res['fields']
        data = res['data']
        df = pd.DataFrame(data, columns=fields)
        
        # 自動鎖定欄位名稱
        col_id = [c for c in fields if '代號' in c][0]
        col_name = [c for c in fields if '名稱' in c][0]
        col_foreign = [c for c in fields if '外' in c and '買賣超' in c][0]
        col_trust = [c for c in fields if '投信買賣超' in c][0]
        
        df[col_foreign] = pd.to_numeric(df[col_foreign].astype(str).str.replace(',', ''), errors='coerce')
        df[col_trust] = pd.to_numeric(df[col_trust].astype(str).str.replace(',', ''), errors='coerce')
        df['total_net'] = df[col_foreign] + df[col_trust]
        
        top10 = df.nlargest(10, 'total_net')
        
        msg = f"🦞【無情法人全場掃描｜{target_date.strftime('%Y-%m-%d')}】\n"
        msg += f"⚔️ 官方外資投信聯手 Top 10：\n\n"
        
        for _, row in top10.iterrows():
            net_buy = int(row['total_net'] / 1000)
            if net_buy > 0:
                msg += f"🔥 {row[col_name]} ({row[col_id]}): 合計淨買 {net_buy} 張\n"
        
        send_msg(msg)

except:
    # 靜默處理，如果抓不到資料或伺服器忙碌，直接跳過，不跳紅字煩你
    pass
