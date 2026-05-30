import os
import requests
import pandas as pd
from datetime import datetime, timedelta

# 🛡️ 安全防護：總鑰匙從金庫讀取
BOT_TOKEN = os.getenv('BOT_TOKEN')
# 🎯 務實折衷：信箱號碼直接寫死，安全且省事
CHAT_ID = "8543567603" 

def send_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

def get_data(date_str):
    url = f"https://api.finmindtrade.com/api/v4/data?dataset=InstitutionalInvestorsBuySell&date={date_str}"
    return requests.get(url).json().get('data', [])

try:
    target_date = datetime.now()
    data = []
    for _ in range(7):
        date_str = target_date.strftime('%Y-%m-%d')
        data = get_data(date_str)
        if data: break
        target_date -= timedelta(days=1)

    if not data:
        send_msg("🦞 龍蝦雷達：近7天無法人資料，請確認是否休市。")
    else:
        df = pd.DataFrame(data)
        col = 'stock_id' if 'stock_id' in df.columns else df.columns[0]
        
        df['net'] = df['buy'] - df['sell']
        top = df.groupby(col)['net'].sum().nlargest(5)
        
        msg = f"🦞【無情法人佈局雷達｜{date_str}】\n"
        msg += f"⚔️ 游擊目標已鎖定，請配合技術面進行最後確認：\n\n"
        
        for s, n in top.items():
            msg += f"🎯 標的 {s}: 法人淨買入 {int(n/1000)} 張\n"
            
        msg += "\n💡 戰略提醒：確認突破20日均線且量能充足，再納入建倉計畫！"
        
        send_msg(msg)

except Exception as e:
    send_msg(f"🦞 龍蝦系統異常：{str(e)}")
