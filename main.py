import requests
import pandas as pd

bot_token = "8885153743:AAEjhEazpexj2j-Az-UzaOQWBy4mNl45KMY"
chat_id = "8543567603"

def send_msg(text):
    requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": text})

try:
    # 改用「每日股價」資料庫，這個保證週末也能撈到週五的結算資料
    url = "https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&start_date=2026-05-29"
    response = requests.get(url).json()
    data = response.get('data', [])
    
    if not data:
        send_msg("🦞 龍蝦回報：今日 API 資料庫有點狀況，週一開盤後將恢復正常。")
    else:
        df = pd.DataFrame(data)
        # 計算當日漲跌幅
        df['pct'] = (df['close'] - df['close_price_previous']) / df['close_price_previous'] * 100
        top = df.nlargest(5, 'pct')
        
        msg = f"🦞【市場強勢獵物｜週五收盤結算】\n\n"
        for _, row in top.iterrows():
            msg += f"🎯 {row['stock_id']}: {row['close']}元 (漲幅 {row['pct']:.2f}%)\n"
        send_msg(msg)

except Exception as e:
    send_msg(f"🦞 龍蝦除錯：{str(e)}")
