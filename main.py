import os
import requests
from datetime import datetime, timedelta

# 🛡️ 總鑰匙從金庫讀取
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603" 

# 🎯 戰術狙擊名單：精準追蹤你的核心部位
WATCHLIST = ["2330", "2317", "2454", "0050", "3231"]

def send_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

try:
    # 🕒 週末強制倒帶：因為今天是週六，我們強制回推 1 天去抓週五的資料
    target_date = datetime.now() - timedelta(days=1)
    date_str = target_date.strftime('%Y-%m-%d')
    
    msg = f"🦞【無情法人狙擊雷達｜{date_str} 補發戰報】\n⚔️ 核心名單籌碼狀況：\n\n"
    
    for stock_id in WATCHLIST:
        # 精準狙擊
        url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInstitutionalInvestorsBuySell&data_id={stock_id}&start_date={date_str}"
        res = requests.get(url).json()
        
        data = res.get('data', [])
        if data:
            latest = data[-1]
            net_buy = int((latest['buy'] - latest['sell']) / 1000)
            
            icon = "🔥 外資投信狂買" if net_buy > 0 else "🧊 法人冷淡撤退"
            msg += f"🎯 {stock_id}: {icon} {abs(net_buy)} 張\n"
        else:
            msg += f"⏳ {stock_id}: 該日無交易數據\n"
            
    msg += "\n💡 戰術紀律：嚴格檢視量能與均線，不符條件絕不盲目建倉。"
    
    send_msg(msg)

except Exception as e:
    send_msg(f"🦞 系統異常：{str(e)}")
