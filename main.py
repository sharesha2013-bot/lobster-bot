import requests
import pandas as pd
from datetime import datetime, timedelta

# ===== Telegram =====
BOT_TOKEN = "改成你的BOT_TOKEN"
CHAT_ID = "改成你的CHAT_ID"

# ===== FinMind =====
FINMIND_TOKEN = "改成你的FINMIND_TOKEN"

def send_msg(text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": text
        }
    )

def get_trade_date():
    today = datetime.now()

    # 星期六抓星期五
    if today.weekday() == 5:
        today = today - timedelta(days=1)

    # 星期日抓星期五
    elif today.weekday() == 6:
        today = today - timedelta(days=2)

    return today.strftime("%Y-%m-%d")

try:

    trade_date = get_trade_date()

    url = "https://api.finmindtrade.com/api/v4/data"

    params = {
        "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
        "start_date": trade_date,
        "end_date": trade_date,
        "token": FINMIND_TOKEN
    }

    response = requests.get(url, params=params)
    data = response.json().get("data", [])

    if len(data) == 0:
        send_msg(f"🦞 {trade_date} 沒抓到法人資料")
        raise Exception("No Data")

    df = pd.DataFrame(data)

    msg = f"🦞【法人布局雷達】\n"
    msg += f"日期：{trade_date}\n\n"

    # 先顯示前20筆測試資料
    for _, row in df.head(20).iterrows():

        stock = row.get("stock_id", "未知")
        investor = row.get("name", "未知法人")

        buy_sell = (
            row.get("buy_sell", 0)
            if row.get("buy_sell") is not None
            else 0
        )

        msg += f"{stock} | {investor} | {buy_sell}\n"

    send_msg(msg)

except Exception as e:

    send_msg(f"🦞 錯誤：{str(e)}")
