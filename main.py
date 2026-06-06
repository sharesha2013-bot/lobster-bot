import os
import time
import requests
import traceback
import pandas as pd
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==========================================
# ⚙️ 系統核心設定
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

class ChipSniper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Referer': 'https://www.twse.com.tw/'
        }
        # 建立具備「自動重試」功能的連線 Session，對付不穩定的網路
        self.session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self.session.headers.update(self.headers)

    def send_telegram(self, text):
        """將分析結果發送至 Telegram，具備自動分段功能"""
        if not BOT_TOKEN:
            print("⚠️ 未設定 BOT_TOKEN，印出於終端機：\n" + text)
            return
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            try:
                self.session.post(url, json={"chat_id": CHAT_ID, "text": chunk}, timeout=10)
                time.sleep(1)
            except Exception as e:
                print(f"Telegram 傳送失敗: {e}")

    def get_latest_trading_days(self, days=2):
        """自動往前尋找最近有開盤的交易日 (避開六日與國定假日)"""
        valid_dates = []
        current_date = datetime.now()
        
        while len(valid_dates) < days:
            d_str = current_date.strftime('%Y%m%d')
            # 使用大盤指數API來確認今天有沒有開盤
            url = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={d_str}&type=IND"
            try:
                res = self.session.get(url, timeout=10).json()
                if res.get('stat') == 'OK':
                    valid_dates.append(d_str)
            except:
                pass
            current_date -= timedelta(days=1)
            time.sleep(1)
            
        return valid_dates

    def fetch_market_data(self, date_str):
        """一次性抓取：法人買賣超(T86)、融資券(MI_MARGN)、每日收盤(MI_INDEX)"""
        market_data = {}
        
        # 1. 抓取每日收盤行情 (取得成交量與股名)
        print(f"📡 抓取 {date_str} 收盤行情...")
        try:
            url_price = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={date_str}&type=ALLBUT0999"
            res = self.session.get(url_price, timeout=10).json()
            if res.get('stat') == 'OK':
                for table in res.get('data9', []): # data9 通常是個股報價
                    sid, name = table[0].strip(), table[1].strip()
                    try:
                        vol = int(table[2].replace(',', '')) // 1000 # 成交張數
                        market_data[sid] = {'name': name, 'vol': vol, 'f_buy': 0, 'it_buy': 0, 'margin_diff': 0}
                    except: continue
        except Exception as e: print(f"收盤資料抓取失敗: {e}")
        time.sleep(2)

        # 2. 抓取三大法人
        print(f"📡 抓取 {date_str} 法人籌碼...")
        try:
            url_inst = f"https://www.twse.com.tw/fund/T86?response=json&date={date_str}&selectType=ALL"
            res = self.session.get(url_inst, timeout=10).json()
            if res.get('stat') == 'OK':
                for row in res['data']:
                    sid = row[0].strip()
                    if sid in market_data:
                        try:
                            f_buy = int(row[4].replace(',', '')) // 1000  # 外資
                            it_buy = int(row[10].replace(',', '')) // 1000 # 投信
                            market_data[sid]['f_buy'] = f_buy
                            market_data[sid]['it_buy'] = it_buy
                        except: continue
        except Exception as e: print(f"法人資料抓取失敗: {e}")
        time.sleep(2)

        # 3. 抓取融資券
        print(f"📡 抓取 {date_str} 融資餘額...")
        try:
            url_margin = f"https://www.twse.com.tw/exchangeReport/MI_MARGN?response=json&date={date_str}&selectType=ALL"
            res = self.session.get(url_margin, timeout=10).json()
            if res.get('stat') == 'OK' and 'data' in res:
                for row in res['data']:
                    sid = row[0].strip()
                    if sid in market_data:
                        try:
                            # 融資(買進-賣出-現金償還)的單日差額
                            margin_buy = int(row[2].replace(',', ''))
                            margin_sell = int(row[3].replace(',', ''))
                            margin_return = int(row[4].replace(',', ''))
                            diff = margin_buy - margin_sell - margin_return
                            market_data[sid]['margin_diff'] = diff
                        except: continue
        except Exception as e: print(f"融資資料抓取失敗: {e}")
        
        return market_data

    def run_strategy(self):
        try:
            print("🦞 啟動【機構級籌碼狙擊系統】...")
            dates = self.get_latest_trading_days(1)
            if not dates:
                self.send_telegram("⚠️ 系統未能取得近日交易資料。")
                return
                
            latest_date = dates[0]
            data = self.fetch_market_data(latest_date)
            
            # --- 籌碼分析邏輯 ---
            it_lock = []      # 投信鎖碼
            dual_buy = []     # 土洋合買
            retail_bleed = [] # 散戶割肉 (法人買+融資減)
            
            for sid, info in data.items():
                if info['vol'] < 1500: continue # 剔除死魚股 (單日成交量<1500張)
                if len(sid) != 4: continue      # 只看普通股
                
                f_b = info['f_buy']
                it_b = info['it_buy']
                vol = info['vol']
                m_diff = info['margin_diff']
                
                # 策略 1: 投信鎖碼 (投信買超 > 500張 且 佔總成交量 > 5%)
                if it_b > 500 and (it_b / vol) > 0.05:
                    it_lock.append(f"🎯 {sid} {info['name']} | 投信大買 {it_b} 張 (佔量 {round((it_b/vol)*100, 1)}%)")
                    
                # 策略 2: 土洋合買 (外資與投信皆買超 > 500張)
                if f_b > 500 and it_b > 500:
                    dual_buy.append(f"🤝 {sid} {info['name']} | 外資 {f_b} 張 / 投信 {it_b} 張")
                    
                # 策略 3: 散戶割肉 (法人總買超 > 1000張，且融資大減 > 500張)
                if (f_b + it_b) > 1000 and m_diff < -500:
                    retail_bleed.append(f"🩸 {sid} {info['name']} | 法人收貨 {f_b+it_b} 張 / 融資退場 {m_diff} 張")

            # --- 組合報表 ---
            msg = f"📊【量化籌碼戰情室】結算日: {latest_date}\n\n"
            
            msg += "🔥 投信狂暴鎖碼 (單日重壓)\n" + ("="*25) + "\n"
            msg += "\n".join(it_lock) if it_lock else "無符合標的"
            msg += "\n\n"
            
            msg += "💎 土洋聯手強買 (大戶共識)\n" + ("="*25) + "\n"
            msg += "\n".join(dual_buy) if dual_buy else "無符合標的"
            msg += "\n\n"
            
            msg += "📉 散戶割肉區 (法人買 + 融資退)\n" + ("="*25) + "\n"
            msg += "\n".join(retail_bleed) if retail_bleed else "無符合標的"
            
            self.send_telegram(msg)
            print("✅ 分析完畢，報表已發送！")
            
        except Exception as e:
            error_trace = traceback.format_exc()
            self.send_telegram(f"⚠️ 系統嚴重異常:\n{str(e)}\n{error_trace[:300]}")

if __name__ == "__main__":
    sniper = ChipSniper()
    sniper.run_strategy()
