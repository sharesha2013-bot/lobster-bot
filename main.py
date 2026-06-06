import os
import time
import requests
import traceback
import concurrent.futures
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
# 📊 教科書級：主力買超熱度分級模組
# ==========================================
def get_heat_level_tag(net_buy_shares):
    """根據買超張數給予教科書級別的熱度標籤"""
    lots = net_buy_shares / 1000  # 換算成張數
    
    if lots >= 80000:
        return " 🌋[Lv.4 核爆]"
    elif lots >= 30000:
        return " 🔥[Lv.3 沸騰]"
    elif lots >= 10000:
        return " ♨️[Lv.2 加溫]"
    elif lots >= 5000:
        return " ☕[Lv.1 微溫]"
    else:
        return ""

# ==========================================
# 🦅 不死鳥濾網 (PRO版：精準剔除幽靈K線)
# ==========================================
def check_undying_bird(stock_id):
    try:
        df = yf.Ticker(f"{stock_id}.TW").history(period="5d")
        if df.empty or len(df) < 2:
            df = yf.Ticker(f"{stock_id}.TWO").history(period="5d")
            
        df = df[df['Volume'] > 0]
        if len(df) < 2: 
            return False
            
        today_close = df['Close'].iloc[-1]
        yesterday_close = df['Close'].iloc[-2]
        
        pct_change = ((today_close - yesterday_close) / yesterday_close) * 100
        
        if pct_change >= -1.5:
            return True
            
        return False
    except:
        return False

# ==========================================
# 🌍 總體經濟與大盤風向
# ==========================================
def get_macro_score():
    score = 0
    try:
        vix = yf.Ticker("^VIX").history(period="2d")
        if len(vix) >= 2:
            vix_pct = ((vix['Close'].iloc[-1] - vix['Close'].iloc[-2]) / vix['Close'].iloc[-2]) * 100
            if vix['Close'].iloc[-1] > 20 or vix_pct > 5: score += 25
        
        usd = yf.Ticker("DX-Y.NYB").history(period="2d")
        if len(usd) >= 2:
            usd_pct = ((usd['Close'].iloc[-1] - usd['Close'].iloc[-2]) / usd['Close'].iloc[-2]) * 100
            if usd_pct > 0.3: score += 25
        
        gold = yf.Ticker("GC=F").history(period="2d")
        if len(gold) >= 2:
            gold_pct = ((gold['Close'].iloc[-1] - gold['Close'].iloc[-2]) / gold['Close'].iloc[-2]) * 100
            if gold_pct > 1.0: score += 25
        
        oil = yf.Ticker("CL=F").history(period="2d")
        if len(oil) >= 2:
            oil_pct = ((oil['Close'].iloc[-1] - oil['Close'].iloc[-2]) / oil['Close'].iloc[-2]) * 100
            if oil_pct > 2.0: score += 25
    except:
        pass 
    return score

def get_us_tech():
    try:
        sox = yf.Ticker("^SOX").history(period="2d")
        tsm = yf.Ticker("TSM").history(period="2d")
        
        if len(sox) >= 2 and len(tsm) >= 2:
            sox_pct = ((sox['Close'].iloc[-1] - sox['Close'].iloc[-2]) / sox['Close'].iloc[-2]) * 100
            tsm_pct = ((tsm['Close'].iloc[-1] - tsm['Close'].iloc[-2]) / tsm['Close'].iloc[-2]) * 100
            return f"🇺🇸【美股風向球】費城半導體: {sox_pct:+.2f}% ｜ 台積電 ADR: {tsm_pct:+.2f}%\n"
    except:
        return "🇺🇸【美股風向球】夜盤數據讀取中斷\n"
    return ""

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
        score = get_macro_score()
        if score >= 75:
            macro_msg = f"🚨【全球防禦警報：{score} 分】市場風暴來襲，請啟動絕對防禦！\n"
        elif score >= 50:
            macro_msg = f"⚠️【全球風險評估：{score} 分】市場出現烏雲，建議觀望保守。\n"
        else:
            macro_msg = f"🟢【全球風險評估：{score} 分】全球市場安全，焦點看個股籌碼。\n"

        us_tech_msg = get_us_tech()

        target_date = datetime.now()
        data_found = False
        
        for _ in range(7):
            d_str = target_date.strftime('%Y%m%d')
            url = f"https://www.twse.com.tw/fund/T86?response=json&date={d_str}&selectType=ALL"
            
            try:
                # 🛡️ 隱身裝甲：暫停 2 秒，避免被證交所機關槍掃射
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
                                'id': stock_id, 'name': name, 'f_net': f_net, 't_net': t_net, 'net': net
                            })
                        except: continue
                
                stocks.sort(key=lambda x: x['net'], reverse=True)
                
                # 🎯 替換為全新的散戶流失濾網
                pro_msg = scan_retail_decrease(stocks)
                
                msg = f"🦞【戰情室 Pro 散戶狙擊版｜{target_date.strftime('%Y-%m-%d')}】\n"
                msg += macro_msg
                msg += us_tech_msg
                msg += pro_msg 
                
                msg += "\n🔥 買超 Top 10:\n"
                for s in stocks[:10]:
                    heat_tag = get_heat_level_tag(s['net'])
                    msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張{heat_tag}\n"
                    
                msg += "\n⚠️ 倒貨 Top 10:\n"
                for s in stocks[-10:][::-1]:
                    bird_tag = " 🦅[不死鳥]" if check_undying_bird(s['id']) else ""
                    msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張{bird_tag}\n"
                    
                msg += "\n🎯【主力狙擊鏡｜土洋合買】:\n"
                count = 0
                for s in stocks:
                    if s['f_net'] > 0 and s['t_net'] > 0 and s['net'] > 1000000: 
                        msg += f"⚡ {s['id']} {s['name']}: 共買 {int(s['net']/1000)} 張 (外{int(s['f_net']/1000)}/投{int(s['t_net']/1000)})\n"
                        count += 1
                    if count >= 5: break
                    
                if count == 0:
                    msg += "今日無外資投信同步鎖碼個股。\n"
                    
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
