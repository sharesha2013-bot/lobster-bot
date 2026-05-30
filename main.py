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
    found = False
    
    for _ in range(7):
        time.sleep(3)
        d_str = target_date.strftime('%Y%m%d')
        url = f"https://www.twse.com.tw/twse/exchange/fund/T86?response=json&date={d_str}&selectType=ALL"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
        
        if res.get('stat') == 'OK':
            fields = res['fields']
            df = pd.DataFrame(res['data'], columns=fields)
            
            # 清洗數值
            df['net'] = pd.to_numeric(df[fields[4]].str.replace(',', ''), errors='coerce') + \
                        pd.to_numeric(df[fields[8]].str.replace(',', ''), errors='coerce')
            df['vol'] = pd.to_numeric(df[fields[7]].str.replace(',', ''), errors='coerce')
            
            # --- 核心改進：嚴格過濾 ---
            # 1. 剔除成交量為0的錯誤資料 (這是造成 inf% 的兇手)
            df = df[df['vol'] > 0]
            df['ratio'] = df['net'] / df['vol']
            
            # --- 產生報表 1：法人買超大象 ---
            top10 = df.nlargest(10, 'net')
            msg = f"🦞【法人戰情室｜{target_date.strftime('%Y-%m-%d')}】\n"
            for _, row in top10.iterrows():
                msg += f"🔥 {row[fields[1]]}: {int(row['net']/1000)} 張\n"
            
            # --- 產生報表 2：主力狙擊鏡 (排除權值股，專找籌碼集中度高) ---
            # 邏輯：排除掉那些權值股 (我們以成交量作為分水嶺)，專注於法人佔比高的標的
            snipers = df[(df['net'] > 500) & (df['ratio'] > 0.05) & (df['vol'] < 10000000)].nlargest(5, 'ratio')
            
            msg += f"\n🎯【主力狙擊鏡】\n"
            if not snipers.empty:
                for _, row in snipers.iterrows():
                    msg += f"⚡ {row[fields[1]]}: 佔比 {round(row['ratio']*100, 2)}%\n"
            
            send_msg(msg)
            found = True
            break
        target_date -= timedelta(days=1)
except:
    pass
