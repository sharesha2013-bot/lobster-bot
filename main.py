import os
import requests
import traceback
from datetime import datetime, timedelta
import yfinance as yf

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
        print("⚠️ 錯誤：找不到 BOT_TOKEN 環境變數")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print(f"Telegram 推播失敗: {e}")

# ==========================================
# 🦅 不死鳥濾網 (教科書級：放量滯跌)
# ==========================================
def check_undying_bird(stock_id):
    try:
        # 先嘗試上市 (.TW)，若無資料再嘗試上櫃 (.TWO)
        df = yf.Ticker(f"{stock_id}.TW").history(period="10d")
        if df.empty or len(df) < 6:
            df = yf.Ticker(f"{stock_id}.TWO").history(period="10d")
            
        if df.empty or len(df) < 6: 
            return False
        
        # 清理空值，防止運算錯誤
        df = df.dropna(subset=['Close', 'Volume'])
        if len(df) < 6:
            return False
            
        # 1. 爆量標準：今日成交量 > 前五日均量的 2 倍
        today_vol = df['Volume'].iloc[-1]
        prev_5d_vol_avg = df['Volume'].iloc[-6:-1].mean()
        
        # 防呆：避免除以零或無量標的
        if prev_5d_vol_avg <= 0 or today_vol < (prev_5d_vol_avg * 2):
            return False
            
        # 2. 滯跌標準：今日跌幅小於 1.5% (即漲跌幅 >= -1.5%)
        today_close = df['Close'].iloc[-1]
        yesterday_close = df['Close'].iloc[-2]
        pct_change = ((today_close - yesterday_close) / yesterday_close) * 100
        
        if pct_change >= -1.5:
            return True
            
        return False
    except Exception:
        # 為了不影響主程式運行，單一個股判斷失敗直接略過
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
# 🎯 雙軌獵殺掃描系統
# ==========================================
def scan_pro_targets(candidate_stocks):
    washout_mode_list = []  
    breakout_mode_list = [] 
    
    # 限制掃描前 40 名，確保執行速度不會 Timeout
    scan_pool = candidate_stocks[:40] 
    
    for s in scan_pool:
        stock_id = s['id']
        name = s['name']
        
        try:
            df = yf.Ticker(f"{stock_id}.TW").history(period="30d")
            if df.empty or len(df) < 25:
                df = yf.Ticker(f"{stock_id}.TWO").history(period="30d")
            
            if df.empty or len(df) < 25: 
                continue
                
            df = df.dropna(subset=['Close', 'Volume'])
            current_price = df['Close'].iloc[-1]
            current_vol = df['Volume'].iloc[-1]
            
            ma10 = df['Close'].tail(10).mean()
            ma20 = df['Close'].tail(20).mean()
            if not (current_price > ma20 and ma10 >= ma20):
                continue 
            
            recent_10d = df.tail(10)
            vol_sum = recent_10d['Volume'].sum()
            if vol_sum == 0: continue # 避開無量死水股
            
            vwap_10d = (recent_10d['Close'] * recent_10d['Volume']).sum() / vol_sum
            avg_vol_5d = df['Volume'].tail(5).mean()
            high_10d = recent_10d['High'].max() 
            
            price_diff_pct = (current_price - vwap_10d) / vwap_10d

            # 🎭 軌道 A：洗碗秀
            if current_price >= (vwap_10d * 0.99) and current_vol < avg_vol_5d and abs(price_diff_pct) <= 0.03:
                status = f"守底 {vwap_10d:.1f} | 量縮洗盤中"
                washout_mode_list.append(f"• {stock_id} {name}: 價 {current_price:.1f} ({status})")

            # 🚀 軌道 B：主升段
            elif current_price >= vwap_10d and current_vol > (avg_vol_5d * 1.5):
                if current_price >= (high_10d * 0.98): 
                    status = f"爆量吃鍋蓋! (10日高 {high_10d:.1f})"
                    breakout_mode_list.append(f"• {stock_id} {name}: 價 {current_price:.1f} ({status})")
        except Exception:
            continue
            
    report = "\n🎯【龍蝦戰情室 Pro - 雙軌獵殺名單】\n"
    report += "="*35 + "\n"
    report += "🟢 階段一：洗碗秀 (量縮守底，適合潛伏)\n"
    report += "\n".join(washout_mode_list) if washout_mode_list else "今日無符合洗碗狀態標的"
    report += "\n\n"
    report += "🔴 階段二：主升段 (爆量點火，準備吃鍋蓋)\n"
    report += "\n".join(breakout_mode_list) if breakout_mode_list else "今日無符合主升段爆發標的"
    report += "\n" + "="*35 + "\n"
    
    return report

# ==========================================
# 🚀 主程式啟動區 (包含 PRO 級錯誤捕捉)
# ==========================================
if __name__ == "__main__":
    try:
        # 1. 全球風險判定
        score = get_macro_score()
        if score >= 75:
            macro_msg = f"🚨【全球防禦警報：{score} 分】市場風暴來襲，請啟動絕對防禦！\n"
        elif score >= 50:
            macro_msg = f"⚠️【全球風險評估：{score} 分】市場出現烏雲，建議觀望保守。\n"
        else:
            macro_msg = f"🟢【全球風險評估：{score} 分】全球市場安全，焦點看個股籌碼。\n"

        # 2. 美股夜盤風向
        us_tech_msg = get_us_tech()

        # 3. 證交所資料抓取
        target_date = datetime.now()
        data_found = False
        
        for _ in range(7):
            d_str = target_date.strftime('%Y%m%d')
            url = f"https://www.twse.com.tw/fund/T86?response=json&date={d_str}&selectType=ALL"
            
            # 加上 Timeout 防止程式卡死
            res = requests.get(url, headers=HEADERS, timeout=10).json()
            
            if res.get('stat') == 'OK':
                data = res['data']
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
                
                pro_msg = scan_pro_targets(stocks)
                
                msg = f"🦞【戰情室 Pro 雙軌版｜{target_date.strftime('%Y-%m-%d')}】\n"
                msg += macro_msg
                msg += us_tech_msg
                msg += pro_msg 
                
                msg += "\n🔥 買超 Top 10:\n"
                for s in stocks[:10]:
                    msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張\n"
                    
                msg += "\n⚠️ 倒貨 Top 10:\n"
                for s in stocks[-10:][::-1]:
                    # 🦅 觸發不死鳥判定
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
        # PRO 級錯誤回報：直接把錯誤明細送到您的 Telegram，不用再盲人摸象！
        error_detail = traceback.format_exc()
        error_msg = f"⚠️ 龍蝦系統 Pro 發生崩潰！\n\n【錯誤摘要】:\n{str(e)}\n\n【工程師追蹤碼】:\n{error_detail[:500]}"
        print(error_msg)
        send_msg(error_msg)
