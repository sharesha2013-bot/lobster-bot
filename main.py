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

def analyze_主力籌碼(stock_id):
    # 這裡實作你的籌碼偵察邏輯框架
    # 邏輯：主力家數差 < 0 且 5日集中度 > 0 才視為主力吃貨
    # 目前為模擬邏輯，你可以隨時調整閾值
    return True 

try:
    target_date = datetime.now()
    found = False
    
    # 循環尋找最近的有效開盤日
    for _ in range(7):
        time.sleep(3)
        d_str = target_date.strftime('%Y%m%d')
        url = f"https://www.twse.com.tw/fund/T86?response=json&date={d_str}&selectType=ALL"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        res = requests.get(url, headers=headers).json()
        
        if res.get('stat') == 'OK':
            fields = res['fields']
            df = pd.DataFrame(res['data'], columns=fields)
            
            # 計算淨買超
            col_id = [c for c in fields if '代號' in c][0]
            col_name = [c for c in fields if '名稱' in c][0]
            col_foreign = [c for c in fields if '外' in c and '買賣超' in c][0]
            col_trust = [c for c in fields if '投信買賣超' in c][0]
            
            df[col_foreign] = pd.to_numeric(df[col_foreign].astype(str).str.replace(',', ''), errors='coerce')
            df[col_trust] = pd.to_numeric(df[col_trust].astype(str).str.replace(',', ''), errors='coerce')
            df['total_net'] = df[col_foreign] + df[col_trust]
            
            # 戰略過濾：找出法人買超前 10 名
            top10 = df.nlargest(10, 'total_net')
            
            msg = f"🦞【籌碼偵察機｜{target_date.strftime('%Y-%m-%d')}】\n"
            msg += f"⚔️ 法人 Top 10 中，真正的主力鎖碼標的：\n\n"
            
            count = 0
            for _, row in top10.iterrows():
                # 這裡調用你的主力偵察邏輯
                if analyze_主力籌碼(row[col_id]):
                    net = int(row['total_net'] / 1000)
                    msg += f"🔥 {row[col_name]}({row[col_id]}): 合計買 {net} 張\n"
                    count += 1
            
            if count == 0:
                msg += "⚠️ 今日法人名單中，無符合主力鎖碼條件之標的。"
            
            send_msg(msg)
            found = True
            break
        
        target_date -= timedelta(days=1)
except:
    pass
