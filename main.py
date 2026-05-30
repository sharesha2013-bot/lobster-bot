import os
import requests
import pandas as pd
from datetime import datetime, timedelta

# 🛡️ 總鑰匙從金庫讀取
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603" 

def send_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

def get_data(date_str):
    # 🎯 不設定特定股票，直接抓全市場！(已修正正確資料庫名稱)
    url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInstitutionalInvestorsBuySell&date={date_str}"
    res = requests.get(url).json()
    return res.get('data', [])

try:
    # 🕒 自動往前找有開盤的日子 (解決週末休市問題)
    target_date = datetime.now() - timedelta(days=1)
    data = []
    for _ in range(7):
        date_str = target_date.strftime('%Y-%m-%d')
        data = get_data(date_str)
        if data: 
            break
        target_date -= timedelta(days=1)

    if not data:
        send_msg("🦞 龍蝦雷達：近7天無法人資料，請確認 API 狀態。")
    else:
        df = pd.DataFrame(data)
        
        # 算出每一筆的「淨買超」(買進 - 賣出)
        df['net'] = df['buy'] - df['sell']
        
        # 把同一檔股票的不同法人(外資/投信)買賣超加總
        grouped = df.groupby('stock_id')['net'].sum().reset_index()
        
        # 👑 直接抓出全市場淨買超「前 10 名」
        top10 = grouped.nlargest(10, 'net')
        
        msg = f"🦞【無情法人全場掃描｜{date_str}】\n"
        msg += f"⚔️ 今日全市場法人淨買超排行榜：\n\n"
        
        for _, row in top10.iterrows():
            stock_id = row['stock_id']
            net_buy = int(row['net'] / 1000) # 換算成張數
            if net_buy > 0:
                msg += f"🔥 代號 {stock_id}: 淨買入 {net_buy} 張\n"
            
        msg += "\n💡 將軍視角：請從上方排行榜中，親自挑選符合游擊條件的標的！"
        
        send_msg(msg)

except Exception as e:
    send_msg(f"🦞 龍蝦系統異常：{str(e)}")
