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
    target_date = datetime.now()
    
    # 強制重試找資料
    for _ in range(7):
        time.sleep(3)
        d_str = target_date.strftime('%Y%m%d')
        url = f"https://www.twse.com.tw/fund/T86?response=json&date={d_str}&selectType=ALL"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        
        if res.get('stat') == 'OK':
            fields = res['fields']
            df = pd.DataFrame(res['data'], columns=fields)
            
            # 整理數據
            df['net'] = pd.to_numeric(df[fields[4]].str.replace(',', ''), errors='coerce') + \
                        pd.to_numeric(df[fields[8]].str.replace(',', ''), errors='coerce')
            
            # 🎯 暴力過濾器：只留「合計買超 > 5000 張」的精銳
            top_filtered = df[df['net'] > 5000].nlargest(10, 'net')
            
            msg = f"🦞【籌碼狙擊鏡｜{target_date.strftime('%Y-%m-%d')}】\n"
            msg += f"⚔️ 已過濾掉 5000 張以下的雜訊，只留精銳：\n\n"
            
            for _, row in top_filtered.iterrows():
                net_buy = int(row['net'] / 1000)
                msg += f"🔥 {row[fields[1]]}({row[fields[0]]}): 合計買 {net_buy} 張\n"
            
            send_msg(msg)
            break
        target_date -= timedelta(days=1)
except:
    pass
