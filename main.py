import os
import requests
import pandas as pd
from datetime import datetime
import time

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

def send_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

try:
    # 強制設定為最後一個交易日：2026/05/29
    d_str = "20260529" 
    url = f"https://www.twse.com.tw/fund/T86?response=json&date={d_str}&selectType=ALL"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
    
    if res.get('stat') == 'OK':
        fields = res['fields']
        df = pd.DataFrame(res['data'], columns=fields)
        df['net'] = pd.to_numeric(df[fields[4]].str.replace(',', ''), errors='coerce') + \
                    pd.to_numeric(df[fields[8]].str.replace(',', ''), errors='coerce')
        df['vol'] = pd.to_numeric(df[fields[7]].str.replace(',', ''), errors='coerce')
        df = df[df['vol'] > 0]
        df['ratio'] = df['net'] / df['vol']
        
        # 1. 買超 Top 10
        top10 = df.nlargest(10, 'net')
        msg = f"🦞【戰情室驗證報告｜{d_str}】\n🔥 買超 Top 10:\n"
        for _, row in top10.iterrows():
            msg += f"• {row[fields[1]]}: {int(row['net']/1000)} 張\n"
        
        # 2. 賣超 Top 10
        bottom10 = df.nsmallest(10, 'net')
        msg += "\n⚠️ 倒貨 Top 10:\n"
        for _, row in bottom10.iterrows():
            msg += f"• {row[fields[1]]}: {int(row['net']/1000)} 張\n"
        
        # 3. 狙擊鏡
        snipers = df[(df['net'] > 500) & (df['ratio'] > 0.05) & (df['vol'] < 10000000)].nlargest(5, 'ratio')
        msg += "\n🎯【狙擊鏡】:\n"
        for _, row in snipers.iterrows():
            msg += f"⚡ {row[fields[1]]}: {round(row['ratio']*100, 2)}%\n"
        
        send_msg(msg)
    else:
        send_msg("❌ 抓取資料失敗，請確認證交所 API 回應。")
except Exception as e:
    send_msg(f"⚠️ 程式發生錯誤: {str(e)}")
