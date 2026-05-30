import requests
import pandas as pd

bot_token = "8885153743:AAEjhEazpexj2j-Az-UzaOQWBy4mNl45KMY"
chat_id = "8543567603"

def send_msg(text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

try:
    url = "https://api.finmindtrade.com/api/v4/data?dataset=InstitutionalInvestorsBuySell&date=2026-05-29"
    response = requests.get(url).json()
    data = response.get('data', [])
    
    if not data:
        send_msg("🦞 報告大俠，今日無法人數據。")
    else:
        df = pd.DataFrame(data)
        col = 'stock_id' if 'stock_id' in df.columns else df.columns[0]
        df['net'] = df['buy'] - df['sell']
        top = df.groupby(col)['net'].sum().nlargest(5)
        
        msg = "🦞【法人今日掃貨榜】\n\n"
        for s, n in top.items():
            msg += f"🎯 {s}: {int(n/1000)} 張\n"
        send_msg(msg)

except Exception as e:
    send_msg(f"🦞 錯誤回報：{str(e)}")
