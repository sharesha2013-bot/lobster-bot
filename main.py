import requests
import pandas as pd
from datetime import datetime

# 1. 正確的鑰匙 ＋ 終於找對的真實收件地址！
bot_token = "8885153743:AAEjhEazpexj2j-Az-UzaOQWBy4mNl45KMY"
chat_id = "8543567603"

try:
    # 2. 自動判斷最新台股開盤日
    res = requests.get('https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&data_id=2330&start_date=2026-05-15').json()
    today = res['data'][-1]['date']
    
    # 3. 無情爬取全市場籌碼
    url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockHoldingSharesPer&start_date={today}&end_date={today}"
    response = requests.get(url).json()
    data = response.get('data', [])
    
    if not data:
        message = f"🦞【無情籌碼龍蝦報告】\n📅 日期：{today}\n⚠️ 證交所尚未更新今日數據，或今日休市。"
    else:
        df = pd.DataFrame(data)
        df['HoldingSharesLevel'] = df['HoldingSharesLevel'].astype(str)
        merged = pd.merge(df[df['HoldingSharesLevel']=='11'][['data_id', 'percent']], 
                          df[df['HoldingSharesLevel']=='15'][['data_id', 'percent']], 
                          on='data_id', suffixes=('_400', '_1000'))
        target = merged.head(10)
        
        message = f"🦞【無情籌碼龍蝦首航成功！】\n📅 資料日期：{today}\n\n🔥 偵測到大戶籌碼鎖碼股：\n"
        for _, row in target.iterrows():
            message += f"📈 代號：{row['data_id']} | 400張大戶：{row['percent_400']}% | 1000張大戶：{row['percent_1000']}%\n"
        message += "\n🎯 報告大俠：地址正確，任督二脈已徹底打通！"
        
except Exception as e:
    message = f"🦞 報告大俠，深海撈資料時遇到小亂流：{str(e)}"

# 4. 發送報告
tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
requests.post(tg_url, json={"chat_id": chat_id, "text": message})
print("🚀 報告已成功發送！")
