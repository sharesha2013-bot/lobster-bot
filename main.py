import os
import requests
from datetime import datetime

# 🛡️ 總鑰匙從金庫讀取
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603" 

# 🎯 戰術狙擊名單：在這裡填入你真正想建倉、觀察的代號
WATCHLIST = ["2330", "2317", "2454", "0050", "3231"]

def send_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

try:
    today = datetime.now().strftime('%Y-%m-%d')
    msg = f"🦞【無情法人狙擊雷達｜{today}】\n⚔️ 核心名單籌碼戰報：\n\n"
    
    for stock_id in WATCHLIST:
        # 精準狙擊：只抓名單內的股票，資料量極小，保證不當機
        url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInstitutionalInvestorsBuySell&data_id={stock_id}&start_date={today}"
        res = requests.get(url).json()
        
        data = res.get('data', [])
        if data:
            # 取得最新一筆法人數據
            latest = data[-1]
            net_buy = int((latest['buy'] - latest['sell']) / 1000)
            
            # 判斷是買超還賣超，加上對應符號
            icon = "🔥" if net_buy > 0 else "🧊"
            msg += f"{icon} {stock_id}: 淨買入 {net_buy} 張\n"
        else:
            msg += f"⏳ {stock_id}: 尚未更新今日資料\n"
            
    msg += "\n💡 戰術紀律：嚴格檢視量能與均線，不符條件絕不盲目建倉。"
    
    send_msg(msg)

except Exception as e:
    send_msg(f"🦞 系統異常：{str(e)}")
