import requests
import pandas as pd

bot_token = "8885153743:AAEjhEazpexj2j-Az-UzaOQWBy4mNl45KMY"
chat_id = "8543567603"

# 🦞 核心改進：不塞死代號！改用「法人關注度」作為第一篩選門檻
def get_dynamic_watchlist():
    # 這裡讓龍蝦先抓出「今天法人買超最多的前 100 檔」
    # 這就是最活、最熱、主力正在關注的池子，不用我們人工塞代號！
    url = "https://api.finmindtrade.com/api/v4/data?dataset=InstitutionalInvestorsBuySell&date=2026-05-29"
    data = requests.get(url).json().get('data', [])
    df = pd.DataFrame(data)
    # 取出法人買賣超總和最大的前 100 檔股票
    top_stocks = df.groupby('stock_id')['buy'].sum().nlargest(100).index.tolist()
    return top_stocks

try:
    message = f"🦞【無情籌碼龍蝦｜全自動AI獵場版】\n\n"
    
    # 自動抓取今日法人最愛的 100 檔獵場
    target_stocks = get_dynamic_watchlist()
    a_list, b_list = [], []
    
    for stock in target_stocks:
        # 在這 100 檔裡面做你的法人連買嚴選... (以此類推你的7大濾網)
        # 這裡放入簡單邏輯示範，後續我們每天根據報告微調即可
        a_list.append(f"🎯 {stock}")
        if len(a_list) >= 5: break

    message += "🔥【主力重點獵物】(這幾檔今天法人狂敲)\n" + "\n".join(a_list)
    message += "\n\n💡 代號已抓出，請大俠過目，挑出想看的丟給我，我們來細看財報與月線！"

except Exception as e:
    message = f"🦞 雷達遇到亂流：{str(e)}"

requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": message})
