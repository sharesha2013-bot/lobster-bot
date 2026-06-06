import os
import requests
import traceback
from datetime import datetime

# ==========================================
# ⚙️ 設定區
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

def send_telegram(text):
    """ 強制發送訊息，確保你能收到結果 """
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=15)
        if resp.status_code != 200:
            print(f"發送失敗: {resp.text}")
    except Exception as e:
        print(f"連線失敗: {e}")

def main():
    try:
        d_str = datetime.now().strftime('%Y%m%d')
        url = f"https://www.twse.com.tw/r/t86?date={d_str}&selectType=ALL"
        headers = {"User-Agent": "Mozilla/5.0"}
        
        # 進行抓取
        resp = requests.get(url, headers=headers, timeout=10)
        
        # 錯誤判斷：若網路連線失敗
        if resp.status_code != 200:
            send_telegram(f"❌ 錯誤：無法連接證交所 (Status: {resp.status_code})")
            return

        data = resp.json()
        
        # 錯誤判斷：若 API 有回應但資料結構不對
        if 'data' not in data:
            send_telegram("❌ 錯誤：API 回應結構異常，可能無交易資料。")
            return
            
        # 邏輯判斷：若有回應但資料為空 (如假日)
        if len(data['data']) == 0:
            send_telegram(f"ℹ️ 狀態：{datetime.now().strftime('%Y-%m-%d')} 無交易資料 (今日休市)。")
            return

        # 執行過濾邏輯
        report_list = []
        for row in data['data']:
            try:
                sid, name = row[0].strip(), row[1].strip()
                fn = int(row[4].replace(',', ''))
                tn = int(row[10].replace(',', ''))
                net = fn + tn
                if net > 5000:
                    report_list.append(f"• {sid} {name}: {net}張")
            except: continue
            
        if report_list:
            msg = f"🦞【籌碼精算戰報｜{d_str}】\n\n🎯 法人合計買超 > 5000張:\n"
            msg += "\n".join(report_list[:15])
            send_telegram(msg)
        else:
            send_telegram("⚠️ 系統執行正常：今日無股票符合「法人買超 > 5000張」的條件。")

    except Exception as e:
        # 詳細回報錯誤內容
        error_msg = f"❌ 程式發生錯誤:\n{str(e)}\n\n{traceback.format_exc()[:200]}"
        send_telegram(error_msg)

if __name__ == "__main__":
    main()
