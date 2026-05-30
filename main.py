import requests
import pandas as pd
from datetime import datetime, timedelta

bot_token = "8885153743:AAEjhEazpexj2j-Az-UzaOQWBy4mNl45KMY"
chat_id = "8543567603"

def send_msg(text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

try:
    # 嘗試抓取日期：如果是週末，就往前推 1~2 天
    target_date = datetime.now().strftime('%Y-%m-%d')
    url = f"https://api.finmindtrade.com/api/v4/data?dataset=InstitutionalInvestorsBuySell&date={target_date}"
    response = requests.get(url).json()
    
    # 如果抓不到資料，我們自動往前推一天抓週五的
    if not response.get('data'):
        target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        url = f"https://api.finmindtrade.com/api/v4/data?dataset=InstitutionalInvestorsBuySell&date={target_date}"
        response = requests.get(url).json()

    data = response.get('data', [])
    
    if not data:
        send_msg(f"🦞 報告大俠，{target_date} 查無法人數據。")
    else:
        df = pd.DataFrame(data)
        col = 'stock_id' if 'stock_id' in df.columns else df.columns[0]
        df['net'] = df['buy'] - df['sell']
        top = df.groupby(col)['net'].sum().nlargest(5)
        
        msg = f"🦞【法人掃貨榜｜{target_date}】\n\n"
        for s, n in top.items():
            msg += f"🎯 {s}: {int(n/1000)} 張\n"
        send_msg(msg)

except Exception as e:
    send_msg(f"🦞 龍蝦補丁錯誤：{str(e)}")
