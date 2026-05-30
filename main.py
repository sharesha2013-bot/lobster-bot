import requests
import pandas as pd
from datetime import datetime, timedelta

# 1. 填入你的 Telegram 秘密通道（這兩行千萬不要改動）
bot_token = "7053535215:AAGZlA8_g1vDk-gY-Qv_w9m29K7hBihX9wE"
chat_id = "5545582998"

# 2. 自動判斷最新台股有開盤的日期（破解週末休市）
try:
    res = requests.get('https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&data_id=2330&start_date=2026-05-15').json()
    today = res['data'][-1]['date']
    print(f"🦞 自動鎖定最新台股交易日：{today}")
except Exception as e:
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"無法取得最新日期，維持今日：{today}")

# 3. 無情爬取全市場籌碼
url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockHoldingSharesPer&start_date={today}&end_date={today}"

try:
    response = requests.get(url).json()
    data = response.get('data', [])
    
    if not data:
        message = f"🦞【無情籌碼龍蝦報告】\n📅 日期：{today}\n⚠️ 證交所尚未更新今日數據，或今日為休市日。"
    else:
        df = pd.DataFrame(data)
        # 轉換持股級距為整型
        df['HoldingSharesLevel'] = df['HoldingSharesLevel'].astype(str)
        
        # 過濾出 400張以上大戶(11級以上) 與 1000張以上超大戶(15級)
        level_11 = df[df['HoldingSharesLevel'] == '11'].copy()
        level_15 = df[df['HoldingSharesLevel'] == '15'].copy()
        
        # 改名以便合併
        level_11.rename(columns={'percent': 'percent_400'}, inplace=True)
        level_15.rename(columns={'percent': 'percent_1000'}, inplace=True)
        
        # 合併數據
        merged = pd.merge(level_11[['data_id', 'percent_400']], level_15[['data_id', 'percent_1000']], on='data_id', how='inner')
        
        # 簡單抓取前 5 檔作為範例（實務上可根據策略篩選）
        target_stocks = merged.head(10)['data_id'].tolist()
        
        message = f"🦞【無情籌碼龍蝦首航成功！】\n📅 資料日期：{today}\n\n🔥 偵測到大戶籌碼鎖碼股（範例）：\n"
        for stock in target_stocks:
            stock_df = merged[merged['data_id'] == stock]
            p400 = stock_df['percent_400'].values[0]
            p1000 = stock_df['percent_1000'].values[0]
            message += f"📈 代號：{stock} | 400張大戶：{p400}% | 1000張大戶：{p1000}%\n"
            
        message += "\n🎯 提示：以上為測試首航，連線機制與大腦已完美打通！"

except Exception as e:
    message = f"🦞 龍蝦在深海撈網時發生了點小意外：{str(e)}"

# 4. 把報告發送到你的 Telegram 手機裡
tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
payload = {
    "chat_id": chat_id,
    "text": message
}
requests.post(tg_url, json=payload)
print("🚀 報告已發送至 Telegram！")
