import os
import requests
import traceback
import concurrent.futures
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd

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

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
}

def send_msg(text):
    if not BOT_TOKEN: return
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except: pass

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
    except: pass

    try:
        otc = yf.Ticker("^TWO").history(period="1mo")
        if len(otc) >= 2 and ((otc['Close'].iloc[-1] - otc['Close'].iloc[-2]) / otc['Close'].iloc[-2]) * 100 < -1.0: 
            score += 45; reasons.append("🩸櫃買下殺")
    except: pass

    try:
        twii = yf.Ticker("^TWII").history(period="1mo")
        if len(twii) >= 2 and ((twii['Close'].iloc[-1] - twii['Close'].iloc[-2]) / twii['Close'].iloc[-2]) * 100 < -1.0:
            score += 30; reasons.append("💀大盤下殺")
    except: pass
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
    except: return ""
    return ""

# ==========================================
# 🎯 核心大腦：龍蝦雷達 X (七刀引擎)
# ==========================================
def analyze_stock(args):
    stock, target_date_str, rank, macro_score = args
    stock_id = stock['id']
    try:
        ticker = yf.Ticker(f"{stock_id}.TW")
        df = ticker.history(period="1mo")
        if df.empty: 
            ticker = yf.Ticker(f"{stock_id}.TWO")
            df = ticker.history(period="1mo")
            
        df = df[df['Volume'] > 0].dropna(subset=['Close', 'Volume'])
        if len(df) < 20: return None
        
        df.index = df.index.tz_localize(None)
        df['date_str'] = df.index.strftime('%Y%m%d')
        if target_date_str not in df['date_str'].values: return None
            
        target_idx = df.index.get_loc(df[df['date_str'] == target_date_str].index[0])
        df = df.iloc[:target_idx + 1]
        if len(df) < 20: return None
        current, yesterday = df.iloc[-1], df.iloc[-2]
        
        # ⚔️ 第一刀：成交值過濾 (>1億)
        trade_value = current['Close'] * current['Volume']
        if trade_value < 100000000: return None
        
        # 取得股本
        shares_out = None
        try: shares_out = ticker.fast_info.shares
        except: shares_out = ticker.info.get('sharesOutstanding')
        
        # ⚔️ 第三刀：股本怪獸過濾 (<3000億)
        if shares_out:
            market_cap = shares_out * current['Close']
            if market_cap > 300000000000: return None

        # ⚔️ 第四刀：計算 VWAP20 與 Cost Gap
        v20_vol = df['Volume'].tail(20).sum()
        vwap20 = (df['Close'].tail(20) * df['Volume'].tail(20)).sum() / v20_vol if v20_vol > 0 else df['Close'].tail(20).mean()
        cost_gap = (current['Close'] - vwap20) / vwap20
        
        ma5, ma20 = df['Close'].tail(5).mean(), df['Close'].tail(20).mean()
        vol_ratio_yest = current['Volume'] / yesterday['Volume'] if yesterday['Volume'] > 0 else 0
        capital_ratio = stock['net'] / shares_out if shares_out and shares_out > 0 and stock['net'] > 0 else 0

        res = {'stock': stock, 'tier': '', 'washout': False, 'rescue': False, 'monster': False, 'fake_bd': False, 'dry_up': False, 'rod': False, 'current': current, 'tag': '', 'sector': f"[{SECTOR_MAP.get(stock_id, '個股')}]"}
        
        # ⚔️ 第二刀 & 第五刀：游擊隊 S/A/B 評分系統
        if stock['net'] > 0:
            score = 0
            if capital_ratio >= 0.005: score += 20
            if capital_ratio >= 0.008: score += 15
            if vol_ratio_yest >= 2.0: score += 20
            elif vol_ratio_yest >= 1.2: score += 10
            if current['Close'] > ma20: score += 10
            if cost_gap > 0: score += 10
            if stock['f_net'] > 0 and stock['t_net'] > 0: score += 25 # 雙法人純度加成

            if score >= 85: res['tier'] = "🔥[S級獵物]"
            elif score >= 70: res['tier'] = "🔴[A級獵物]"
            elif score >= 55: res['tier'] = "🟢[B級獵物]"

            if res['tier']:
                res['tag'] = f"評分:{score} | 鎖碼:{capital_ratio*100:.2f}% | 量增:{vol_ratio_yest:.1f}倍"

        # ⚔️ 第六刀：妖股雷達 (5日漲20% + 雙法人 + 爆量)
        if len(df) >= 6:
            pct_5d = (current['Close'] - df['Close'].iloc[-6]) / df['Close'].iloc[-6]
            if pct_5d > 0.20 and stock['f_net'] > 0 and stock['t_net'] > 0 and vol_ratio_yest > 1.2:
                res['monster'] = True
                
        # 🚑 自救專區：黃金救援區 -5% ~ -12% 且雙法人點火
        if -0.12 <= cost_gap <= -0.05 and stock['f_net'] > 0 and stock['t_net'] > 0:
            res['rescue'] = True
            res['tag'] = f"Gap:{cost_gap*100:.1f}% | 雙法人急救"

        # 斷頭禁區過濾：放棄救援直接拉黑
        if cost_gap < -0.15:
            return None

        # 舊精華：洗碗秀
        if stock['net'] > 0 and capital_ratio >= 0.001 and (-0.01 <= (current['Close'] - ma5)/ma5 <= 0.03):
            res['washout'] = True
            res['tag'] = f"鎖碼:{capital_ratio*100:.2f}%"

        # 舊精華：極端盤勢防禦
        has_rod = (current['High'] - max(current['Close'], current['Open']) > abs(current['Close'] - current['Open']) * 2)
        if current['Low'] < df['Low'].iloc[-10:-1].min() and current['Close'] > yesterday['Close']: res['fake_bd'] = True
        if current['Volume'] < (df['Volume'].tail(5).mean() * 0.35) and current['Close'] > ma20: res['dry_up'] = True
        if current['Volume'] > (df['Volume'].tail(5).mean() * 1.5) and has_rod: res['rod'] = True

        return res
    except: return None

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
            
        twii = yf.Ticker("^TWII").history(period="10d")
        stocks, etfs = [], []
        d_str, display_date = "", ""
        
        # 🔥 終極週末修復：用上櫃 API 當探測針，找到真正的交易日再啟動
        for offset in range(1, 6):
            latest_date = twii.index[-offset]
            d_str = latest_date.strftime('%Y%m%d')
            display_date = latest_date.strftime('%Y-%m-%d')
            stocks, etfs = [], []
            otc_found = False
            
            # 1. 探測上櫃 (必定需要正確日期才能抓到資料)
            try:
                otc_date = f"{latest_date.year - 1911}/{latest_date.strftime('%m/%d')}"
                res_otc = requests.get(f"https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php?l=zh-tw&o=json&se=EW&t=D&d={otc_date}", headers=HEADERS, timeout=10)
                if res_otc.status_code == 200 and 'aaData' in res_otc.json():
                    aaData = res_otc.json()['aaData']
                    if len(aaData) > 0:
                        otc_found = True  # 確認今天是交易日！
                        for row in aaData:
                            if len(row) > 12:
                                try:
                                    sid = row[0].strip()
                                    fn = int(row[8].replace(',', ''))
                                    tn = int(row[11].replace(',', ''))
                                    net = fn + tn
                                    if sid in ['0050', '0056', '00919', '00929']: etfs.append({'id': sid, 'name': row[1].strip(), 'f_net': fn, 't_net': tn, 'net': net})
                                    elif sid.isdigit() and len(sid) == 4 and not sid.startswith('00'): stocks.append({'id': sid, 'name': row[1].strip(), 'f_net': fn, 't_net': tn, 'net': net})
                                except: continue
            except: pass

            # 2. 如果上櫃有資料，才去抓上市 (上市 OpenAPI 永遠只給最新一天，所以一定吻合)
            if otc_found:
                try:
                    res = requests.get("https://openapi.twse.com.tw/v1/fund/T86_ALL", headers=HEADERS, timeout=10)
                    if res.status_code == 200:
                        for row in res.json():
                            sid = row.get('Code', '').strip()
                            fn = int(str(row.get('ForeignInvestorNetBuy', '0')).replace(',', ''))
                            tn = int(str(row.get('InvestmentTrustNetBuy', '0')).replace(',', ''))
                            net = fn + tn
                            if sid in ['0050', '0056', '00919', '00929']: etfs.append({'id': sid, 'name': row.get('Name', '').strip(), 'f_net': fn, 't_net': tn, 'net': net})
                            elif not sid.startswith('00'): stocks.append({'id': sid, 'name': row.get('Name', '').strip(), 'f_net': fn, 't_net': tn, 'net': net})
                except: pass
                break # 成功找到交易日並抓取完畢，跳出迴圈！

        if not stocks:
            send_msg(f"❌ 雷達警告：已回溯 5 個交易日無資料。")
        else:
            # ⚔️ 第七刀：ETF 風向球分析
            etf_msg = ""
            etf_buys = [e for e in etfs if e['f_net'] > 5000000 or e['t_net'] > 5000000]
            if etf_buys:
                etf_names = [e['id'] for e in etf_buys]
                etf_msg = f"📡【ETF 風向球】：{', '.join(etf_names)} 大買 ｜ 系統風險偏好回升！\n"
            else:
                etf_msg = f"📡【ETF 風向球】：大資金觀望中。\n"

            stocks.sort(key=lambda x: x['net'], reverse=True)
            scan_args = [(s, d_str, i + 1, score) for i, s in enumerate(stocks[:200])] + [(s, d_str, 999, score) for s in stocks[-50:]]
            
            s_list, a_list, b_list, washout_list, rescue_list, monster_list = [], [], [], [], [], []
            fake_bd_list, dry_up_list, rod_list = [], [], []
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                results = list(executor.map(analyze_stock, scan_args))
                
            for res in results:
                if not res: continue
                s, price, tag, sector = res['stock'], res['current']['Close'], res['tag'], res['sector']
                line = f"• {sector} {s['id']} {s['name']}: 價 {price:.1f} ({tag})"
                
                if res['monster']: monster_list.append(f"🚀[妖股] {line}")
                if res['tier'] == "🔥[S級獵物]": s_list.append(line)
                elif res['tier'] == "🔴[A級獵物]": a_list.append(line)
                elif res['tier'] == "🟢[B級獵物]": b_list.append(line)
                elif res['washout']: washout_list.append(line)
                
                if res['rescue']: rescue_list.append(line)
                if res['fake_bd']: fake_bd_list.append(f"• {sector} {s['id']} {s['name']}: 價 {price:.1f}")
                if res['dry_up']: dry_up_list.append(f"• {sector} {s['id']} {s['name']}: 價 {price:.1f}")
                if res['rod']: rod_list.append(f"• {sector} {s['id']} {s['name']}: 價 {price:.1f} (爆量被出貨)")

            # 🔥 補回：投信無情結帳
            it_dump_list = sorted([s for s in stocks if s['t_net'] < -2000000], key=lambda x: x['t_net'])[:5]
            
            # 🔥 補回：買超 Top 5
            top5_msg = ""
            for s in stocks[:5]:
                net_k = int(s['net']/1000)
                if net_k >= 20000: icon = "🔥[Lv.3 沸騰]"
                elif net_k >= 10000: icon = "♨️[Lv.2 加溫]"
                elif net_k >= 5000: icon = "🔥[Lv.1 點火]"
                else: icon = ""
                top5_msg += f"• {s['id']} {s['name']}: {net_k} 張 {icon}\n"

            # 🔥 補回：土洋合買狙擊鏡
            co_buy_msg = ""
            for s in stocks[:100]:
                if s['f_net'] > 0 and s['t_net'] > 0:
                    fk, tk, net_k = int(s['f_net']/1000), int(s['t_net']/1000), int(s['net']/1000)
                    if net_k >= 1000:
                        co_buy_msg += f"⚡ {s['id']} {s['name']}: 共買 {net_k} 張 (外{fk}/投{tk})\n"
            
            # ================= 戰報組合 =================
            msg = f"🦞【戰情室 X 終極完全體｜{display_date}】\n"
            msg += etf_msg + macro_msg
            
            msg += "\n🎯【主力獵殺區｜七刀精選 S/A/B 菁英】\n========================\n"
            if monster_list: msg += f"{chr(10).join(monster_list)}\n\n"
            if s_list: msg += f"🔥 [S級獵物]\n{chr(10).join(s_list)}\n"
            if a_list: msg += f"🔴 [A級獵物]\n{chr(10).join(a_list)}\n"
            if b_list: msg += f"🟢 [B級獵物]\n{chr(10).join(b_list)}\n"
            if not (s_list or a_list or b_list or monster_list): msg += "無符合標準獵物。\n"
            
            msg += f"\n🧼 洗碗秀 (大戶護盤伏擊)\n{chr(10).join(washout_list) if washout_list else '無'}\n"
            
            msg += "\n🚑【逆境送分題｜主力自救突圍區】\n========================\n"
            msg += f"{chr(10).join(rescue_list) if rescue_list else '無符合標的'}\n"
            
            msg += "\n🥷【闇黑兵法｜極端吃屍區】\n========================\n"
            msg += f"🪤 破底翻 (假跌破真誘空)\n{chr(10).join(fake_bd_list) if fake_bd_list else '無'}\n"
            msg += f"🩸 終極窒息量 (主力偷偷鎖碼)\n{chr(10).join(dry_up_list) if dry_up_list else '無'}\n"
            
            msg += "\n💀【高危雷區｜請勿接刀】\n========================\n"
            msg += "🔪 投信無情結帳:\n"
            msg += "".join([f"• {s['id']} {s['name']}: 賣 {abs(int(s['t_net']/1000))} 張\n" for s in it_dump_list]) if it_dump_list else "無\n"
            msg += f"⚡ 散戶絞肉機 (避雷針):\n{chr(10).join(rod_list) if rod_list else '無'}\n"
            
            msg += f"\n🔥 買超 Top 5 (大戶動向):\n{top5_msg}"
            
            msg += "\n⚠️ 倒貨警報 (不死鳥):\n"
            found_bird = False
            for s in stocks[-10:][::-1]:
                bird_tag = check_undying_bird(s['id'], d_str)
                if bird_tag:
                    msg += f"• {s['id']} {s['name']}: {int(s['net']/1000)} 張{bird_tag}\n"
                    found_bird = True
            if not found_bird: msg += "無\n"

            msg += f"\n🎯【主力狙擊鏡｜土洋合買】:\n{co_buy_msg if co_buy_msg else '無'}\n"
            
            send_msg(msg)

    except Exception as e:
        send_msg(f"⚠️ 龍蝦系統核心崩潰！\n{str(e)}\n{traceback.format_exc()[:300]}")
