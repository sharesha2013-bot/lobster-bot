import os
import time
import requests
import traceback
from datetime import datetime, timedelta, timezone
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==========================================
# ⚙️ 系統設定：法人籌碼集中度雷達
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

class ChipRanking:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Connection': 'keep-alive'
        }
        self.session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self.session.headers.update(self.headers)

    def send_telegram(self, text):
        if not BOT_TOKEN:
            print("⚠️ 未設定 BOT_TOKEN，以下為終端機輸出：\n\n" + text)
            return
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            try:
                self.session.post(url, json={"chat_id": CHAT_ID, "text": chunk}, timeout=10)
                time.sleep(1)
            except Exception as e:
                print(f"推播失敗: {e}")

    def get_latest_trading_day(self):
        """強制鎖定台灣時區，往前回溯尋找最新交易日"""
        tw_tz = timezone(timedelta(hours=8))
        current = datetime.now(tw_tz)
        print(f"📡 啟動雷達，目前台灣時間: {current.strftime('%Y-%m-%d %H:%M:%S')}")

        for _ in range(7):
            d_str = current.strftime('%Y%m%d')
            url = f"https://www.twse.com.tw/fund/T86?response=json&date={d_str}&selectType=ALL"
            try:
                res = self.session.get(url, timeout=10).json()
                if res.get('stat') == 'OK' and len(res.get('data', [])) > 0:
                    print(f"🎯 成功鎖定最新交易日: {d_str}")
                    return d_str
            except: pass
            current -= timedelta(days=1)
            time.sleep(1.5)
        return None

    def fetch_data(self, date_str):
        """抓取收盤量價與三大法人籌碼"""
        market = {}
        
        # 1. 抓取收盤價與成交量
        print("📡 正在下載全市場成交量...")
        try:
            url_price = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={date_str}&type=ALLBUT0999"
            res = self.session.get(url_price, timeout=10).json()
            if res.get('stat') == 'OK':
                for t in res.get('data9', []):
                    sid, name = t[0].strip(), t[1].strip()
                    try:
                        # 排除權證與 ETF，只抓普通股 (長度為4)
                        if len(sid) == 4:
                            market[sid] = {
                                'name': name, 
                                'vol': int(t[2].replace(',','')) // 1000, # 換算成張
                                'f_buy': 0, 
                                'it_buy': 0
                            }
                    except: continue
        except Exception as e: print(f"收盤資料抓取失敗: {e}")
        time.sleep(2)

        # 2. 抓取法人買賣超
        print("📡 正在下載法人籌碼...")
        try:
            url_inst = f"https://www.twse.com.tw/fund/T86?response=json&date={date_str}&selectType=ALL"
            res = self.session.get(url_inst, timeout=10).json()
            if res.get('stat') == 'OK':
                for row in res['data']:
                    sid = row[0].strip()
                    if sid in market:
                        try:
                            # 抓取外資與投信買賣超 (換算成張)
                            market[sid]['f_buy'] = int(row[4].replace(',','')) // 1000
                            market[sid]['it_buy'] = int(row[10].replace(',','')) // 1000
                        except: continue
        except Exception as e: print(f"法人資料抓取失敗: {e}")
        
        return market

    def generate_ranking(self):
        try:
            date_str = self.get_latest_trading_day()
            if not date_str:
                self.send_telegram("⚠️ 雷達未能取得近七日交易資料。")
                return

            data = self.fetch_data(date_str)
            ranking_list = []
            
            for sid, info in data.items():
                vol = info['vol']
                f_buy = info['f_buy']
                it_buy = info['it_buy']
                total_inst_buy = f_buy + it_buy
                
                # 濾網 1：單日總成交量必須大於 1000 張 (排除沒流動性的死魚)
                # 濾網 2：法人總買超必須是大於 0 (排除法人正在倒貨的)
                if vol >= 1000 and total_inst_buy > 0:
                    concentration = (total_inst_buy / vol) * 100
                    ranking_list.append({
                        'sid': sid,
                        'name': info['name'],
                        'ratio': concentration,
                        'total_buy': total_inst_buy,
                        'vol': vol,
                        'f': f_buy,
                        'it': it_buy
                    })
                    
            # 依照「集中度 (ratio)」由大到小排序
            ranking_list.sort(key=lambda x: x['ratio'], reverse=True)
            
            # 取出最強的 Top 20
            top_20 = ranking_list[:20]
            
            # --- 組合精美戰報 ---
            msg = f"📊【單日法人籌碼集中度 Top 20】\n"
            msg += f"📅 結算日: {date_str}\n"
            msg += f"📌 條件: 成交量>1000張，由(外資+投信)佔比排序\n"
            msg += "="*30 + "\n\n"
            
            for i, stock in enumerate(top_20, 1):
                msg += f"🏆 No.{i} | {stock['sid']} {stock['name']}\n"
                msg += f"🎯 集中度: {stock['ratio']:.1f}%\n"
                msg += f"📦 法人狂掃: {stock['total_buy']} 張 (佔總量 {stock['vol']} 張)\n"
                msg += f"   (外資: {stock['f']} 張 / 投信: {stock['it']} 張)\n"
                msg += "-"*25 + "\n"
                
            self.send_telegram(msg)
            print("✅ 籌碼集中度排行榜已發送！")

        except Exception as e:
            self.send_telegram(f"⚠️ 系統崩潰:\n{str(e)}\n{traceback.format_exc()[:300]}")

if __name__ == "__main__":
    radar = ChipRanking()
    radar.generate_ranking()
