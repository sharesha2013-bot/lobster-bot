import requests
import pandas as pd

bot_token = "8885153743:AAEjhEazpexj2j-Az-UzaOQWBy4mNl45KMY"
chat_id = "8543567603"

def send_msg(text):
    requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": text})

try:
    # 暴力解法：直接抓取最近 5 天的資料，不指定單一天份
    url = "https://api.finmindtrade.com/api/v4/data?dataset=InstitutionalInvestorsBuySell&start_date=2026-05-25"
    response = requests.get(url).json()
    data = response.get('data', [])
    
    if not data:
        send_msg("🦞 龍蝦回報：API 目前抓不到資料，可能是資料庫維護中。")
    else:
        df = pd.DataFrame(data)
        # 找出資料庫中「最新」的那一天
        latest_date = df['date'].max()
        df_latest = df[df['date'] == latest_date]
        
        col = 'stock_id' if 'stock_id' in df.columns else df.columns[0]
        df_latest = df_latest.copy()
        df_latest['net'] = df_latest['buy'] - df_latest['sell']
        
        top = df_latest.groupby(col)['net'].sum().nlargest(5)
        
        msg = f"🦞【法人最新戰報｜{latest_date}】\n\n"
        for s, n in top.items():
            msg += f"🎯 {s}: {int(n/1000)} 張\n"
        send_msg(msg)

except Exception as e:
    send_msg(f"🦞 龍蝦暴力補丁錯誤：{str(e)}")
