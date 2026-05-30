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
            df['net'] = pd.to_numeric(df[fields[4]].str.replace(',', ''), errors='coerce') + \
                        pd.to_numeric(df[fields[8]].str.replace(',', ''), errors='coerce')
            df['vol'] = pd.to_numeric(df[fields[7]].str.replace(',', ''), errors='coerce')
            df['ratio'] = df['net'] / df['vol']
            
            # --- 報表 1：法人大象 ---
            top10 = df.nlargest(10, 'net')
            msg1 = f"🦞【法人戰情室｜{target_date.strftime('%Y-%m-%d')}】\n"
            for _, row in top10.iterrows():
                msg1 += f"🔥 {row[fields[1]]}: {int(row['net']/1000)} 張\n"
            
            # --- 報表 2：主力狙擊 (買超 > 500 張 且 佔比 > 15%) ---
            snipers = df[(df['net'] > 500) & (df['ratio'] > 0.15)].nlargest(5, 'ratio')
            msg2 = f"\n🎯【主力狙擊鏡｜{target_date.strftime('%Y-%m-%d')}】\n"
            if not snipers.empty:
                for _, row in snipers.iterrows():
                    msg2 += f"⚡ {row[fields[1]]}: 佔比 {round(row['ratio']*100, 2)}% (主力鎖碼)\n"
            else:
                msg2 += "無符合鎖碼條件之標的。"
            
            send_msg(msg1 + msg2)
            break
        target_date -= timedelta(days=1)
except:
    pass
