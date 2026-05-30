import os
import requests
import pandas as pd
from datetime import datetime

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

def send_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

try:
    d_str = "20260529"
    url = f"https://www.twse.com.tw/fund/T86?response=json&date={d_str}&selectType=ALL"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).json()
    
    if res.get('stat') == 'OK':
        data = res['data']
        # 建立 DF，確保數字轉換絕對安全
        df = pd.DataFrame(data)
        
        # 欄位對應 (這是最穩定的抓法)
        # 0:代號, 1:名稱, 4:外資買賣超, 7:成交股數, 8:投信買賣超
        df.columns = ['ID', 'Name', '2', '3', 'Foreign', '5', '6', 'Vol', 'Trust', '9']
        
        for col in ['Foreign', 'Trust', 'Vol']:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
        df['net'] = df['Foreign'] + df['Trust']
        # 預防除以零
        df['ratio'] = df.apply(lambda x: (x['net'] / x['Vol']) if x['Vol'] > 0 else 0, axis=1)
        
        # 1. 買超 Top 10
        top10 = df.nlargest(10, 'net')
        msg = f"🦞【戰情報告｜{d_str}】\n🔥 買超 Top 10:\n"
        for _, row in top10.iterrows():
            msg += f"• {row['Name']}: {int(row['net']/1000)} 張\n"
        
        # 2. 倒貨 Top 10
        bottom10 = df.nsmallest(10, 'net')
        msg += "\n⚠️ 倒貨 Top 10:\n"
        for _, row in bottom10.iterrows():
            msg += f"• {row['Name']}: {int(row['net']/1000)} 張\n"
        
        # 3. 狙擊鏡 (篩選邏輯：成交量大於5000張，且法人佔比 > 5%)
        snipers = df[(df['net'] > 500000) & (df['Vol'] > 5000000) & (df['ratio'] > 0.05)].nlargest(5, 'ratio')
        msg += "\n🎯【主力狙擊鏡】:\n"
        if not snipers.empty:
            for _, row in snipers.iterrows():
                msg += f"⚡ {row['Name']}: 佔比 {round(row['ratio']*100, 2)}%\n"
        else:
            msg += "今日無主力鎖碼標的。"
        
        send_msg(msg)
    else:
        send_msg("❌ 抓取資料失敗，證交所回應異常。")
except Exception as e:
    send_msg(f"⚠️ 程式崩潰: {str(e)}")
