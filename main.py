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
    for _ in range(7):
        time.sleep(3)
        d_str = target_date.strftime('%Y%m%d')
        url = f"https://www.twse.com.tw/fund/T86?response=json&date={d_str}&selectType=ALL"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        
        if res.get('stat') == 'OK':
            fields = res['fields']
            df = pd.DataFrame(res['data'], columns=fields)
            
            # 數值清洗
            # 欄位順序：0代號, 1名稱, 4外資買賣超, 8投信買賣超, 7成交股數
            df['net'] = pd.to_numeric(df[fields[4]].str.replace(',', ''), errors='coerce') + \
                        pd.to_numeric(df[fields[8]].str.replace(',', ''), errors='coerce')
            df['vol'] = pd.to_numeric(df[fields[7]].str.replace(',', ''), errors='coerce')
            
            # 🎯 狙擊手核心邏輯：
            # 1. 買超張數 > 1000張 (過濾掉零星買盤)
            # 2. 法人買超佔比 > 10% (這代表這檔股票今天是被法人「鎖定」的)
            df['ratio'] = df['net'] / df['vol']
            top_filtered = df[(df['net'] > 1000) & (df['ratio'] > 0.10)].nlargest(10, 'net')
            
            msg = f"🦞【狙擊手戰情室｜{target_date.strftime('%Y-%m-%d')}】\n"
            msg += f"⚔️ 鎖定：法人吃貨佔成交量 10% 以上之精銳標的：\n\n"
            
            for _, row in top_filtered.iterrows():
                net = int(row['net'] / 1000)
                pct = round(row['ratio'] * 100, 2)
                msg += f"🔥 {row[fields[1]]}({row[fields[0]]}): 買 {net} 張 (法人佔比 {pct}%)\n"
            
            send_msg(msg)
            break
        target_date -= timedelta(days=1)
except:
    pass
