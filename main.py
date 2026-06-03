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
    lots = net_buy_shares / 1000
    if lots >= 80000: return " 🌋[Lv.4 核爆]"
    elif lots >= 30000: return " 🔥[Lv.3 沸騰]"
    elif lots >= 10000: return " ♨️[Lv.2 加溫]"
    elif lots >= 5000: return " ☕[Lv.1 微溫]"
    return ""

def get_squeeze_tag(borrow_lots):
    """軋空燃料雷達：偵測借券餘額"""
    if borrow_lots >= 300000:
        return f" 🚀[核爆軋空:借券{borrow_lots//10000}萬張]"
    elif borrow_lots >= 100000:
        return f" 🔥[潛力軋空:借券{borrow_lots//10000}萬張]"
    return ""

# ==========================================
# 🦅 不死鳥濾網 2.0 (自帶戰鬥力數值)
# ==========================================
def check_undying_bird(stock_id):
    try:
        df = yf.Ticker(f"{stock_id}.TW").history(period="5d")
        if df.empty or len(df) < 2:
            df = yf.Ticker(f"{stock_id}.TWO").history(period="5d")
            
        df = df[df['Volume'] > 0]
        if len(df) < 2: 
            return ""
            
        today_close = df['Close'].iloc[-1]
        yesterday_close = df['Close'].iloc[-2]
        
        pct_change = ((today_close - yesterday_close) / yesterday_close) * 100
        
        # 只要跌幅小於 1.5%，即視為主力強撐
        if pct_change >= -1.5:
            return f" 🦅[不死鳥 {pct_change:+.1f}%]"
            
        return ""
    except:
        return ""

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
# 🎯 雙軌獵殺掃描系統 (PRO 多執行緒版)
# ==========================================
def fetch_single_stock(stock):
    stock_id = stock['id']
    try:
        df = yf.Ticker(f"{stock_id}.TW").history(period="30d")
        if df.empty or len(df) < 20:
            df = yf.Ticker(f"{stock_id}.TWO").history(period="30d")
        if df.empty or len(df) < 20: 
            return None
            
        df = df[df['Volume'] > 0].dropna(subset=['Close', 'Volume'])
        if len(df) < 20:
            return None
            
        return {'stock': stock, 'df': df}
    except:
        return None

def scan_pro_targets(candidate_stocks):
    washout_mode_list = []  
    breakout_mode_list = [] 
    scan_pool = candidate_stocks[:40] 
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_single_stock, scan_pool))
    
    for res in results:
        if not res: continue
        stock_id = res['stock']['id']
        name = res['stock']['name']
        df = res['df']
        current_price = df['Close'].iloc[-1]
        yesterday_price = df['Close'].iloc[-2]
        current_vol = df['Volume'].iloc[-1]
        ma10 = df['Close'].tail(10).mean()
        ma20 = df['Close'].tail(20).mean()
        
        if not (current_price > ma20 and ma10 >= ma20): continue 
        
        recent_10d = df.tail(10)
        vol_sum = recent_10d['Volume'].sum()
        if vol_sum == 0: continue 
        
        vwap_10d = (recent_10d['Close'] * recent_10d['Volume']).sum() / vol_sum
        avg_vol_5d = df['Volume'].tail(5).mean()
        high_10d = recent_10d['High'].max() 
        price_diff_pct = (current_price - vwap_10d) / vwap_10d

        if current_price >= (vwap_10d * 0.98) and current_vol < (avg_vol_5d * 0.75) and abs(price_diff_pct) <= 0.03:
            status = f"守底 {vwap_10d:.1f} | 量縮洗盤"
            washout_mode_list.append(f"• {stock_id} {name}: 價 {current_price:.1f} ({status})")
        elif current_price >= vwap_10d and current_vol > (avg_vol_5d * 1.5) and current_price > yesterday_price:
            if current_price >= (high_10d * 0.98): 
                status = f"爆量點火! (前高 {high_10d:.1f})"
                breakout_mode_list.append(f"• {stock_id} {name}: 價 {current_price:.1f} ({status})")
            
    report = "\n🎯【龍蝦戰情室 Pro - 雙軌獵殺名單】\n"
    report += "="*35 + "\n"
    report += "🟢 階段一：洗碗秀 (量縮守底，適合潛伏)\n"
    report += "\n".join(washout_mode_list) if washout_mode_list else "今日無符合洗碗狀態標的"
    report += "\n\n"
    report += "🔴 階段二：主升段 (爆量點火，準備吃鍋蓋)\n"
    report += "\n".join(breakout_mode_list) if breakout_mode_list else "今日無符合主升段爆發標的"
    report += "\n" + "="*35 + "\n"
    return report

def get_borrow_data(date_str):
    """偷看外資底牌：智慧爬取當日借券賣出餘額"""
    try:
        url = f"https://www.twse.com.tw/exchangeReport/TWT93U?response=json&date={date_str}"
        time.sleep(1) # 隱身裝甲
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        borrow_dict = {}
        if res.get('stat') == 'OK':
            # 智慧追蹤欄位：自動尋找含有「借券」與「餘額」的欄位索引
            fields = res.get('fields', [])
            target_idx = -1
            for i, f in enumerate(fields):
                if '借券' in f and '餘額' in f:
                    target_idx = i
                    break
            
            # 萬一標頭改版找不到，啟用盲狙預設值(通常在倒數第2或第14欄)
            if target_idx == -1: 
                target_idx = 14 
                
            for row in res['data']:
                try:
                    s_id = row[0].strip()
                    idx = target_idx if target_idx < len(row) else -2
                    balance_shares = int(row[idx].replace(',', '')) 
                    borrow_dict[s_id] = balance_shares // 1000 # 換算成張數
                except: continue
        return borrow_dict
    except:
        return {}

# ==========================================
# 🚀 主程式啟動區
# ==========================================
if __name__ == "__main__":
    try:
        score = get_macro_score()
        if score >= 75: macro_msg = f"🚨【全球防禦警報：{score} 分】市場風暴來襲，請啟動絕對防禦！\n"
        elif score >= 50: macro_msg = f"⚠️【全球風險評估：{score} 分】市場出現烏雲，建議觀望保守。\n"
        else: macro_msg = f"🟢【全球風險評估：{score} 分】全球市場安全，焦點看個股籌碼。\n"

        us_tech_msg = get_us_tech()
        target_date = datetime.now()
        data_found = False
        
        for _ in range(7):
            d_str = target_date.strftime('%Y%m%d')
            url = f"https://www.twse.com.tw/fund/T86?response=json&date={d_str}&selectType=ALL"
            
            try:
                time.sleep(2) 
                res = requests.get(url, headers=HEADERS, timeout=10)
                if res.status_code != 200:
                    target_date -= timedelta(days=1)
                    continue
                res_json = res.json()
            except:
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
                            stocks.append({'id': stock_id, 'name': name, 'f_net': f_net, 't_net': t_net, 'net': f_net + t_net})
                        except: continue
                
                stocks.sort(key=lambda x: x['net'], reverse=True)
                pro_msg = scan_pro_targets(stocks)
                
                # 取得當日借券燃料數據 (修正版)
                borrow_data = get_borrow_data(d_str)
                
                msg = f"🦞【戰情室 Pro 完全體｜{target_date.strftime('%Y-%m-%d')}】\n"
                msg += macro_msg
                msg += us_tech_msg
                msg += pro_msg 
                
                msg += "\n🔥 買超 Top 10 (含軋空燃料):\n"
                for s in stocks[:10]:
                    heat_tag = get_heat_level_tag(s['net'])
                    squeeze_tag = get_squeeze_tag(borrow_data.get(s['id'], 0))
                    msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張{heat_tag}{squeeze_tag}\n"
                    
                msg += "\n⚠️ 倒貨警報 (只列出主力硬扛不死鳥):\n"
                found_bird = False
                for s in stocks[-10:][::-1]:
                    bird_tag = check_undying_bird(s['id'])
                    if bird_tag:
                        msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張{bird_tag}\n"
                        found_bird = True
                if not found_bird:
                    msg += "今日無符合條件的不死鳥標的。\n"
                    
                msg += "\n🎯【主力狙擊鏡｜土洋合買】:\n"
                count = 0
                for s in stocks:
                    if s['f_net'] > 0 and s['t_net'] > 0 and s['net'] > 1000000: 
                        msg += f"⚡ {s['id']} {s['name']}: 共買 {int(s['net']/1000)} 張 (外{int(s['f_net']/1000)}/投{int(s['t_net']/1000)})\n"
                        count += 1
                    if count >= 5: break
                if count == 0: msg += "今日無外資投信同步鎖碼個股。\n"
                    
                send_msg(msg)
                data_found = True
                break
                
            target_date -= timedelta(days=1)
            
        if not data_found: send_msg("❌ 查詢天數內皆無證交所資料，請確認是否逢長假。")

    except Exception as e:
        error_detail = traceback.format_exc()
        error_msg = f"⚠️ 龍蝦系統 Pro 發生崩潰！\n\n【錯誤摘要】:\n{str(e)}\n\n【工程師追蹤碼】:\n{error_detail[:500]}"
        print(error_msg)
        send_msg(error_msg)
