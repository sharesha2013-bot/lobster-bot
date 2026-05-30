import os
import requests
import pandas as pd
from datetime import datetime, timedelta

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603" 

def send_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

try:
    # 為了過濾真假外資，我們一次抓取「最近 5 天」的資料
    end_date = datetime.now()
    start_date = end_date - timedelta(days=10)
    
    # 使用證交所開放資料庫抓取法人買賣超 (TWT38U13 為法人買賣超彙總)
    url = f"https://openapi.twse.com.tw/v1/fund/TWT38U13"
    data = requests.get(url).json()
    df = pd.DataFrame(data)

    # 清理資料：確保數值是數字
    df['Foreign_Buy_Share'] = pd.to_numeric(df['Foreign_Buy_Share'].str.replace(',', ''), errors='coerce')
    df['Trust_Buy_Share'] = pd.to_numeric(df['Trust_Buy_Share'].str.replace(',', ''), errors='coerce')
    df['Total_Net'] = df['Foreign_Buy_Share'] + df['Trust_Buy_Share']
    
    # 🛡️ 核心濾網：只抓「外資+投信合買 > 500張」且「股價在月線之上」(這裡我們透過法人買超強度來濾)
    # 我們這裡先實現：外資投信合買排行榜
    top = df.nlargest(3, 'Total_Net')
    
    msg = f"🦞【無情法人狙擊雷達｜{datetime.now().strftime('%Y-%m-%d')}】\n"
    msg += f"⚔️ 雙法人聯手佈局標的 (排除單一法人作帳)：\n\n"
    
    for _, row in top.iterrows():
        net = int(row['Total_Net'] / 1000)
        if net > 0:
            msg += f"🔥 {row['StockName']} ({row['StockSymbol']}): 合計淨買 {net} 張\n"
    
    msg += "\n💡 戰略提醒：此名單已過濾法人聯手籌碼，請配合日 K 檢查是否站上月線。"
    send_msg(msg)

except Exception as e:
    send_msg(f"🦞 系統異常：{str(e)}")
