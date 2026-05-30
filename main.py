import os
import requests
import pandas as pd

# 🛡️ 總鑰匙從金庫讀取
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603" 

def send_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

try:
    # 🎯 捨棄第三方，直接打證交所官方 API (外資及陸資買賣超彙總表)
    # 官方的好處：自動給最新開盤日，完全不用算日期！
    url = "https://openapi.twse.com.tw/v1/fund/TWT38U13"
    data = requests.get(url).json()
    
    if not data:
        send_msg("🦞 龍蝦雷達：證交所官方資料庫無回應。")
    else:
        df = pd.DataFrame(data)
        
        # 確保數字格式正確 (去除官方資料可能帶有的逗號)
        df['Difference_Share'] = df['Difference_Share'].astype(str).str.replace(',', '')
        df['Difference_Share'] = pd.to_numeric(df['Difference_Share'], errors='coerce')
        
        # 篩選外資淨買超前 5 名
        top = df.nlargest(5, 'Difference_Share')
        date_str = df['Date'].iloc[0]
        
        msg = f"🦞【無情法人佈局雷達｜{date_str}】\n"
        msg += f"⚔️ 官方外資游擊目標已鎖定：\n\n"
        
        for _, row in top.iterrows():
            # 證交所單位是「股」，除以 1000 換算成「張」
            net_buy = int(row['Difference_Share'] / 1000)
            msg += f"🎯 {row['Name']} ({row['Code']}): 外資淨買入 {net_buy} 張\n"
            
        msg += "\n💡 戰略提醒：確認突破 20 日均線且量能充足，再將其納入 100 股建倉計畫！"
        
        send_msg(msg)

except Exception as e:
    send_msg(f"🦞 龍蝦系統異常：{str(e)}")
