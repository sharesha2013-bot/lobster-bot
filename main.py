import os
import requests
import traceback
import concurrent.futures
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import time
import random

# ==========================================
# ⚙️ 系統設定區 & 游擊隊族群字典
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

SECTOR_MAP = {
    '3324': '散熱', '3017': '散熱', '2421': '散熱',
    '1504': '重電', '1513': '重電', '1519': '重電',
    '2368': 'AI伺服器', '3231': 'AI伺服器', '2382': 'AI伺服器',
    '2330': '晶圓代工', '6770': '晶圓代工', '2303': '晶圓代工',
    '2342': '封測', '3049': '面板', '3481': '面板',
    '2371': '綠能', '6901': '創投'
}

# ==========================================
# 🕵️ 模仿人類模組 (反反爬蟲)
# ==========================================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
]

session = requests.Session()

def fetch_api(url, referer):
    # 隨機延遲 1.5 ~ 3.5 秒，完全模擬人類點擊
    time.sleep(random.uniform(1.5, 3.5))
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': referer,
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin'
    }
    try:
        res = session.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            return res.json()
        print(f"HTTP ERROR {res.status_code}: {url}")
        return None
    except Exception as e:
        print(f"Request ERROR: {e}")
        return None

def send_msg(text):
    if not BOT_TOKEN: return
    try: 
        # Telegram 有 4096 字元限制，超過自動分段傳送
        chunk_size = 4000
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i+chunk_size]
            res = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                json={"chat_id": CHAT_ID, "text": chunk}, 
                timeout=10
            )
            if res.status_code != 200:
                print(f"Telegram API Error: {res.text}")
    except Exception as e: 
        print(f"ERROR: Telegram send failed - {e}")

# ==========================================
# 📊 輔助模組 (宏觀天氣與美股)
# ==========================================
def get_macro_score():
    score, reasons = 0, []
    try:
        twd = yf.Ticker("TWD=X").history(period="5d")
        if len(twd) >= 2 and ((twd['Close'].iloc[-1] - twd['Close'].iloc[-2]) / twd['Close'].iloc[-2]) * 100 > 0.2:
            score += 35; reasons.append("💸台幣急貶")
        elif len(twd) >= 1 and twd['Close'].iloc[-1] > 32.5: 
            score += 15; reasons.append("⚠️台幣弱勢")
    except Exception as e: 
        print(f"ERROR: TWD macro failed - {e}")

    try:
        otc = yf.Ticker("^TWO").history(period="1mo")
        if len(otc) >= 2 and ((otc['Close'].iloc[-1] - otc['Close'].iloc[-2]) / otc['Close'].iloc[-2]) * 100 < -1.0: 
            score += 45; reasons.append("🩸櫃買下殺")
    except Exception as e: 
        print(f"ERROR: OTC macro failed - {e}")

    try:
        twii = yf.Ticker("^TWII").history(period="1mo")
        if len(twii) >= 2 and ((twii['Close'].iloc[-1] - twii['Close'].iloc[-2]) / twii['Close'].iloc[-2]) * 100 < -1.0:
            score += 30; reasons.append("💀大盤下殺")
    except Exception as e: 
        print(f"ERROR: TWII macro failed - {e}")
    return score, reasons

def check_undying_bird(stock_id, target_date_str):
    try:
        df = yf.Ticker(f"{stock_id}.TW").history(period="10d")
        if df.empty: df = yf.Ticker(f"{stock_id}.TWO").history(period="10d")
        df.index = df.index.tz_localize(None)
        if target_date_str not in df.index.strftime('%Y%m%d').values: return ""
        idx = df.index.get_loc(df[df.index.strftime('%Y%m%d') == target_date_str].index[0])
        if idx < 1: return "" 
        pct = ((df['Close'].iloc[idx] - df['Close'].iloc[idx-1]) / df['Close'].iloc[idx-1]) * 100
        if pct >= -1.5: return f" 🦅[不死鳥 {pct:+.1f}%]"
    except Exception as e: 
        print(f"ERROR: Undying bird failed for {stock_id} - {e}")
        return ""
    return ""

# ==========================================
# 🎯 核心大腦：三大名單過濾 X (七刀引擎)
# ==========================================
def analyze_stock(args):
    stock, target_date_str, rank, macro_score, inst_history_map = args
    stock_id = stock['id']
    try:
        ticker = yf.Ticker(f"{stock_id}.TW")
        df = ticker.history(period="2mo")
        if df.empty: 
            ticker = yf.Ticker(f"{stock_id}.TWO")
            df = ticker.history(period="2mo")
            
        df = df[df['Volume'] > 0].dropna(subset=['Close', 'Volume'])
        if len(df) < 20: return None
        
        df.index = df.index.tz_localize(None)
        df['date_str'] = df.index.strftime('%Y%m%d')
        if target_date_str in df['date_str'].values:
            target_idx = df.index.get_loc(df[df['date_str'] == target_date_str].index[0])
            df = df.iloc[:target_idx + 1]
            
        if len(df) < 20: return None
        current, yesterday = df.iloc[-1], df.iloc[-2]
        
        trade_value = current['Close'] * current['Volume']
        if trade_value < 100000000: return None
        
        shares_out = None
        try: shares_out = ticker.fast_info.shares
        except Exception as e: 
            try: shares_out = ticker.info.get('sharesOutstanding')
            except Exception as e2: print(f"ERROR: Shares out failed {stock_id} - {e2}")
        
        if shares_out:
            market_cap = shares_out * current['Close']
            if market_cap > 300000000000: return None

        v20_vol = df['Volume'].tail(20).sum()
        vwap20 = (df['Close'].tail(20) * df['Volume'].tail(20)).sum() / v20_vol if v20_vol > 0 else df['Close'].tail(20).mean()
        
        ma5, ma20 = df['Close'].tail(5).mean(), df['Close'].tail(20).mean()
        ma60 = df['Close'].tail(60).mean() if len(df) >= 60 else ma20
        vol_ratio_yest = current['Volume'] / yesterday['Volume'] if yesterday['Volume'] > 0 else 0
        capital_ratio = stock['net'] / shares_out if shares_out and shares_out > 0 and stock['net'] > 0 else 0

        history = inst_history_map.get(stock_id, [])
        consec_days = 0
        cum_buy = 0
        cost_sum = 0
        cost_vol = 0
        
        for h in history:
            net = h['net']
            if net > 0:
                consec_days += 1
                cum_buy += net
                cost_sum += net * df[df['date_str'] == h['date_str']]['Close'].mean() if not df[df['date_str'] == h['date_str']].empty else (net * current['Close'])
                cost_vol += net
            else:
                break 
                
        avg_cost = (cost_sum / cost_vol) if cost_vol > 0 else vwap20
        cost_gap = (current['Close'] - avg_cost) / avg_cost if avg_cost > 0 else 0

        res = {
            'stock': stock, 
            'sector': f"[{SECTOR_MAP.get(stock_id, '個股')}]",
            'current': current,
            'is_rescue': False,
            'is_uptrend': False,
            'is_danger': False,
            'rescue_info': "",
            'uptrend_info': "",
            'danger_info': "",
            'washout': False
        }

        # 🎯 第一區：法人自救區
        is_structure_safe = current['Close'] > ma60
        is_buying_streak = consec_days >= 2 or cum_buy > 2000
        is_pullback = -0.15 <= cost_gap <= -0.02
        
        if is_buying_streak and is_pullback and is_structure_safe:
            res['is_rescue'] = True
            res['rescue_info'] = f"套牢約 {cost_gap*100:.1f}% | 佔股本 {capital_ratio*100:.2f}% | 連買 {consec_days} 天 | 成本約 {avg_cost:.1f} 元"

        # 🚀 第二區：主升段雷達
        is_dual_buy = stock['f_net'] > 0 and stock['t_net'] > 0
        is_trend_up = current['Close'] > ma5 > ma20
        is_vol_up = vol_ratio_yest >= 1.5
        is_breakout = current['Close'] >= df['Close'].tail(10).max()
        
        pct_5d = (current['Close'] - df['Close'].iloc[-6]) / df['Close'].iloc[-6] if len(df) >= 6 else 0
        is_monster = pct_5d > 0.20 and is_dual_buy and is_vol_up
        
        if is_dual_buy and is_trend_up and (is_vol_up or is_breakout or capital_ratio >= 0.005 or is_monster):
            res['is_uptrend'] = True
            monster_tag = "🚀[妖股] " if is_monster else ""
            res['uptrend_info'] = f"{monster_tag}量增 {vol_ratio_yest:.1f}倍 | 佔股本 {capital_ratio*100:.2f}% | 法人買 {stock['net']} 張"

        # 💀 第三區：避雷區
        is_trust_dump = stock['t_net'] < -1000
        is_broken = current['Close'] < ma20
        has_rod = (current['High'] - max(current['Close'], current['Open']) > abs(current['Close'] - current['Open']) * 2) and current['Volume'] > (df['Volume'].tail(5).mean() * 1.5)
        
        if is_trust_dump or (has_rod and is_broken) or (cum_buy == 0 and stock['net'] < -3000):
            res['is_danger'] = True
            res['danger_info'] = f"投信賣 {stock['t_net']} 張 | 跌破均線 | 避雷針現象"

        # 附屬訊號：洗碗秀
        if stock['net'] > 0 and capital_ratio >= 0.001 and (-0.01 <= (current['Close'] - ma5)/ma5 <= 0.03):
            res['washout'] = True
            
        return res
    except Exception as e: 
        print(f"ERROR: analyze_stock failed for {stock_id} - {e}")
        return None

# ==========================================
# 歷史法人資料收集
# ==========================================
def get_historical_inst_data(target_dates):
    history_map = {}
    for d_obj in target_dates:
        d_str = d_obj.strftime('%Y%m%d')
        # 1. 抓上市歷史 (使用舊版穩定端點避免 /r/t86 阻擋)
        twse_url = f"https://www.twse.com.tw/exchangeReport/T86?response=json&date={d_str}&selectType=ALL"
        data_twse = fetch_api(twse_url, referer="https://www.twse.com.tw/zh/trading/foreign/t86.html")
        if data_twse and 'data' in data_twse:
            for row in data_twse['data']:
                try:
                    sid = row[0].strip()
                    fn = int(str(row[4]).replace(',', ''))
                    tn = int(str(row[10]).replace(',', ''))
                    if sid not in history_map: history_map[sid] = []
                    history_map[sid].append({'date_str': d_str, 'f_net': fn, 't_net': tn, 'net': fn + tn})
                except Exception: pass
            
        # 2. 抓上櫃歷史
        otc_date = f"{d_obj.year - 1911}/{d_obj.strftime('%m/%d')}"
        tpex_url = f"https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php?l=zh-tw&o=json&se=EW&t=D&d={otc_date}"
        data_otc = fetch_api(tpex_url, referer="https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge.php")
        if data_otc and 'aaData' in data_otc:
            for row in data_otc['aaData']:
                if len(row) > 12:
                    try:
                        sid = row[0].strip()
                        fn = int(row[8].replace(',', ''))
                        tn = int(row[11].replace(',', ''))
                        if sid not in history_map: history_map[sid] = []
                        history_map[sid].append({'date_str': d_str, 'f_net': fn, 't_net': tn, 'net': fn + tn})
                    except Exception: pass
    
    for sid in history_map:
        history_map[sid] = sorted(history_map[sid], key=lambda x: x['date_str'], reverse=True)
        
    return history_map

# ==========================================
# 🚀 主程式執行區
# ==========================================
if __name__ == "__main__":
    try:
        score, macro_reasons = get_macro_score()
        reason_str = f" [{', '.join(macro_reasons)}]" if macro_reasons else " [環境安定]"
        if score >= 75: macro_msg = f"🚨【環境風險：{score}分】風暴來襲！請空手！{reason_str}\n"
        elif score >= 50: macro_msg = f"⚠️【環境風險：{score}分】警報亮起，縮小部位。{reason_str}\n"
        else: macro_msg = f"🟢【環境風險：{score}分】環境安全，適合游擊。{reason_str}\n"
            
        twii = yf.Ticker("^TWII").history(period="15d")
        if twii.empty:
            send_msg("❌ 雷達警告：無法取得大盤日期基準，請檢查網路連線。")
            exit()
            
        recent_trading_days = twii.index[-5:][::-1]
        stocks, etfs = [], []
        d_str, display_date = "", ""
        valid_d_obj = None

        for d_obj in recent_trading_days:
            test_d_str = d_obj.strftime('%Y%m%d')
            otc_date = f"{d_obj.year - 1911}/{d_obj.strftime('%m/%d')}"
            
            # 使用模擬人類機制測試 TWSE
            url = f"https://www.twse.com.tw/exchangeReport/T86?response=json&date={test_d_str}&selectType=ALL"
            data = fetch_api(url, referer="https://www.twse.com.tw/zh/trading/foreign/t86.html")
            
            if data and 'data' in data and len(data['data']) > 100:
                d_str = test_d_str
                display_date = d_obj.strftime('%Y-%m-%d')
                valid_d_obj = d_obj
                
                # 解析上市
                for row in data['data']:
                    try:
                        sid = row[0].strip()
                        name = row[1].strip()
                        fn = int(str(row[4]).replace(',', ''))
                        tn = int(str(row[10]).replace(',', ''))
                        net = fn + tn
                        if sid in ['0050', '0056', '00919', '00929']: 
                            etfs.append({'id': sid, 'name': name, 'f_net': fn, 't_net': tn, 'net': net})
                        elif not sid.startswith('00'): 
                            stocks.append({'id': sid, 'name': name, 'f_net': fn, 't_net': tn, 'net': net})
                    except Exception: pass
                    
                # 解析上櫃
                url_otc = f"https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php?l=zh-tw&o=json&se=EW&t=D&d={otc_date}"
                data_otc = fetch_api(url_otc, referer="https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge.php")
                if data_otc and 'aaData' in data_otc:
                    for row in data_otc['aaData']:
                        if len(row) > 12:
                            try:
                                sid = row[0].strip()
                                name = row[1].strip()
                                fn = int(row[8].replace(',', ''))
                                tn = int(row[11].replace(',', ''))
                                net = fn + tn
                                if sid in ['0050', '0056', '00919', '00929']: 
                                    etfs.append({'id': sid, 'name': name, 'f_net': fn, 't_net': tn, 'net': net})
                                elif sid.isdigit() and len(sid) == 4 and not sid.startswith('00'): 
                                    stocks.append({'id': sid, 'name': name, 'f_net': fn, 't_net': tn, 'net': net})
                            except Exception: pass
                
                break # 成功找到最近一筆資料就跳出

        if not stocks:
            send_msg(f"❌ 雷達警告：啟動防禦機制後，往前回推 5 個交易日皆無籌碼資料。請稍後再試。")
        else:
            # 取得歷史資料 (往回抓取過去的真實交易日)
            target_idx = twii.index.get_loc(valid_d_obj)
            start_idx = max(0, target_idx - 4)
            target_dates = [twii.index[idx] for idx in range(start_idx, target_idx + 1)][::-1]
            
            inst_history_map = get_historical_inst_data(target_dates)
            
            etf_msg = ""
            etf_buys = [e for e in etfs if e['f_net'] > 5000000 or e['t_net'] > 5000000]
            if etf_buys:
                etf_names = [e['id'] for e in etf_buys]
                etf_msg = f"📡【ETF 風向球】：{', '.join(etf_names)} 大買 ｜ 系統風險偏好回升！\n"
            else:
                etf_msg = f"📡【ETF 風向球】：大資金觀望中。\n"

            stocks.sort(key=lambda x: x['net'], reverse=True)
            scan_args = [(s, d_str, i + 1, score, inst_history_map) for i, s in enumerate(stocks[:200])] + [(s, d_str, 999, score, inst_history_map) for s in stocks[-50:]]
            
            rescue_list, uptrend_list, danger_list, washout_list = [], [], [], []
            total_scanned = len(scan_args)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                results = list(executor.map(analyze_stock, scan_args))
                
            for res in results:
                if not res: continue
                s, price, sector = res['stock'], res['current']['Close'], res['sector']
                
                if res['is_rescue']:
                    rescue_list.append(f"• {sector} {s['id']} {s['name']}: 價 {price:.1f}\n   └ {res['rescue_info']}")
                if res['is_uptrend']:
                    uptrend_list.append(f"• {sector} {s['id']} {s['name']}: 價 {price:.1f}\n   └ {res['uptrend_info']}")
                if res['is_danger']:
                    danger_list.append(f"• {sector} {s['id']} {s['name']}: 價 {price:.1f}\n   └ {res['danger_info']}")
                if res['washout']:
                    washout_list.append(f"• {sector} {s['id']} {s['name']}: 價 {price:.1f}")

            msg = f"🦞【龍蝦雷達 X 終極完全體｜{display_date}】\n"
            msg += etf_msg + macro_msg
            
            msg += "\n📊【系統回測統計】\n========================\n"
            msg += f"今日選股數量: {total_scanned} 檔\n"
            msg += f"法人自救數量: {len(rescue_list)} 檔\n"
            msg += f"主升段數量: {len(uptrend_list)} 檔\n"
            msg += f"避雷數量: {len(danger_list)} 檔\n"
            msg += f"[未來回測] 5日績效: -- | 10日績效: -- | 20日績效: --\n"

            msg += "\n🎯【第一區：法人自救區】\n========================\n"
            msg += f"{chr(10).join(rescue_list) if rescue_list else '無符合標的'}\n"
            
            msg += "\n🚀【第二區：主升段雷達】\n========================\n"
            msg += f"{chr(10).join(uptrend_list) if uptrend_list else '無符合標的'}\n"
            
            msg += "\n💀【第三區：避雷區】\n========================\n"
            msg += f"{chr(10).join(danger_list) if danger_list else '無符合標的'}\n"
            
            msg += f"\n🧼 【附屬訊號：洗碗秀】\n{chr(10).join(washout_list) if washout_list else '無'}\n"
            
            msg += "\n⚠️ 倒貨警報 (不死鳥):\n"
            found_bird = False
            for s in stocks[-10:][::-1]:
                bird_tag = check_undying_bird(s['id'], d_str)
                if bird_tag:
                    msg += f"• {s['id']} {s['name']}: {s['net']} 張{bird_tag}\n"
                    found_bird = True
            if not found_bird: msg += "無\n"
            
            send_msg(msg)

    except Exception as e:
        send_msg(f"⚠️ 龍蝦系統核心崩潰！\n{str(e)}\n{traceback.format_exc()[:300]}")
