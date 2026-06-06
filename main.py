import os
import time
import requests
import traceback
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd

# ==========================================
# ⚙️ 系統設定區
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

# PRO級偽裝：模擬真實瀏覽器，降低被證交所阻擋的機率
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
}

def send_msg(text):
    """傳送 Telegram 訊息"""
    if not BOT_TOKEN:
        print("⚠️ 尚未設定 BOT_TOKEN 環境變數。以下為系統測試輸出：\n")
        print(text)
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print(f"Telegram 推播失敗: {e}")

# ==========================================
# 🎯 單一濾網：散戶持股流失 (3%~5%)
# ==========================================
def scan_retail_decrease(candidate_stocks):
    """
    過濾條件：散戶持股佔比流失 3% ~ 5%
    使用日籌碼替代方案：三大法人單日淨買超佔當日總成交量的 3%~5%
    """
    results_list = []
    
    # 取前 50 檔法人買超名單進行快速換算，避免 API 請求過多超時
    scan_pool = candidate_stocks[:50]
    
    for stock in scan_pool:
        stock_id = stock['id']
        name = stock['name']
        net_inst_buy = stock['net'] # 法人總淨買超 (股)
        
        if net_inst_buy <= 0:
            continue
            
        try:
            df = yf.Ticker(f"{stock_id}.TW").history(period="1d")
            if df.empty:
                df = yf.Ticker(f"{stock_id}.TWO").history(period="1d")
            if df.empty:
                continue
                
            daily_volume_shares = df['Volume'].iloc[-1]
            if daily_volume_shares == 0:
                continue
            
            # 計算散戶流失比例 (法人買走的比例)
            retail_dump_ratio = (net_inst_buy / daily_volume_shares) * 100
            
            # 嚴格篩選：3% 到 5% 之間
            if 3.0 <= retail_dump_ratio <= 5.0:
                results_list.append(f"• {stock_id} {name}: 散戶單日流失 {retail_dump_ratio:.2f}% (法人承接 {int(net_inst_buy/1000)}張)")
                
        except Exception:
            continue
            
    report = "\n🎯【龍蝦戰情室 Pro - 散戶下車 (3%~5%) 狙擊名單】\n"
    report += "="*35 + "\n"
    report += "\n".join(results_list) if results_list else "今日無符合散戶流失 3%~5% 之標的"
    report += "\n" + "="*35 + "\n"
    
    return report

# ==========================================
# 🚀 主程式啟動區
# ==========================================
if __name__ == "__main__":
    try:
        target_date = datetime.now()
        data_found = False
        
        for _ in range(7):
            d_str = target_date.strftime('%Y%m%d')
            url = f"https://www.twse.com.tw/fund/T86?response=json&date={d_str}&selectType=ALL"
            
            try:
                # 🛡️ 隱身裝甲：暫停 2 秒，避免被證交所阻擋
                time.sleep(2) 
                res = requests.get(url, headers=HEADERS, timeout=10)
                
                if res.status_code != 200:
                    print(f"⚠️ 證交所阻擋請求 (狀態碼: {res.status_code})，尋找前一天...")
                    target_date -= timedelta(days=1)
                    continue
                
                res_json = res.json()
                
            except requests.exceptions.RequestException as e:
                print(f"⚠️ 連線失敗: {e}")
                target_date -= timedelta(days=1)
                continue
            except ValueError:
                print("⚠️ 證交所回傳的不是 JSON，可能被擋了或遇到維修！")
                target_date -= timedelta(days=1)
                continue
            
            if res_json.get('stat') == 'OK':
                data = res_json['data']
                stocks = []
                for row in data:
                    if len(row) > 18:
                        try:
                            stock_id = row[0].strip()
                            name = row[1].strip()
                            
                            if stock_id.startswith('00'): continue 
                            
                            f_net = int(row[4].replace(',', '')) if row[4] != '--' else 0
                            t_net = int(row[10].replace(',', '')) if row[10] != '--' else 0
                            net = f_net + t_net
                            stocks.append({
                                'id': stock_id, 'name': name, 'net': net
                            })
                        except: continue
                
                # 依照淨買超張數排序
                stocks.sort(key=lambda x: x['net'], reverse=True)
                
                # 執行乾淨的散戶流失濾網
                pro_msg = scan_retail_decrease(stocks)
                
                msg = f"🦞【戰情室 Pro 極簡狙擊版｜{target_date.strftime('%Y-%m-%d')}】\n"
                msg += pro_msg 
                
                send_msg(msg)
                data_found = True
                break
                
            target_date -= timedelta(days=1)
            
        if not data_found:
            send_msg("❌ 查詢天數內皆無證交所資料，請確認是否逢長假。")

    except ImportError:
        send_msg("⚠️ 系統警報：找不到 yfinance 或 requests 套件！請檢查伺服器環境。")
    except Exception as e:
        error_detail = traceback.format_exc()
        error_msg = f"⚠️ 龍蝦系統 Pro 發生崩潰！\n\n【錯誤摘要】:\n{str(e)}\n\n【工程師追蹤碼】:\n{error_detail[:500]}"
        print(error_msg)
        send_msg(error_msg)
