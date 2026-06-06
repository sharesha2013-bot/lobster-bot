import os
import time
import requests
import traceback
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==========================================
# ⚙️ 系統核心設定 (血犬 PRO)
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = "8543567603"

class Bloodhound:
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
            print(text)
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
        """尋找最近一個有開盤的屠殺日"""
        current = datetime.now()
        for _ in range(7):
            d_str = current.strftime('%Y%m%d')
            url = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={d_str}&type=IND"
            try:
                res = self.session.get(url, timeout=10).json()
                if res.get('stat') == 'OK':
                    return d_str
            except: pass
            current -= timedelta(days=1)
            time.sleep(1)
        return None

    def fetch_blood_data(self, date_str):
        """掃描戰場：行情、法人、融資"""
        market = {}
        
        # 1. 抓收盤量價
        print(f"🐺 嗅探 {date_str} 戰場數據...")
        try:
            url = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={date_str}&type=ALLBUT0999"
            res = self.session.get(url, timeout=10).json()
            if res.get('stat') == 'OK':
                for t in res.get('data9', []):
                    sid, name = t[0].strip(), t[1].strip()
                    try:
                        market[sid] = {'name': name, 'vol': int(t[2].replace(',',''))//1000, 'f':0, 'it':0, 'margin':0}
                    except: continue
        except: pass
        time.sleep(2)

        # 2. 抓主力動向
        print("🐺 鎖定大戶資金流向...")
        try:
            url = f"https://www.twse.com.tw/fund/T86?response=json&date={date_str}&selectType=ALL"
            res = self.session.get(url, timeout=10).json()
            if res.get('stat') == 'OK':
                for row in res['data']:
                    sid = row[0].strip()
                    if sid in market:
                        try:
                            market[sid]['f'] = int(row[4].replace(',',''))//1000
                            market[sid]['it'] = int(row[10].replace(',',''))//1000
                        except: continue
        except: pass
        time.sleep(2)

        # 3. 抓散戶恐慌度 (融資)
        print("🐺 偵測散戶恐慌指數...")
        try:
            url = f"https://www.twse.com.tw/exchangeReport/MI_MARGN?response=json&date={date_str}&selectType=ALL"
            res = self.session.get(url, timeout=10).json()
            if res.get('stat') == 'OK' and 'data' in res:
                for row in res['data']:
                    sid = row[0].strip()
                    if sid in market:
                        try:
                            diff = int(row[2].replace(',','')) - int(row[3].replace(',','')) - int(row[4].replace(',',''))
                            market[sid]['margin'] = diff
                        except: continue
        except: pass
        
        return market

    def hunt(self):
        try:
            date_str = self.get_latest_trading_day()
            if not date_str:
                self.send_telegram("⚠️ 戰場迷霧過濃，無法獲取數據。")
                return

            data = self.fetch_blood_data(date_str)
            
            nuke_list = []
            slaughter_list = []
            demon_list = []
            
            for sid, info in data.items():
                if len(sid) != 4: continue
                v, f, it, m = info['vol'], info['f'], info['it'], info['margin']
                if v <= 0: continue

                # ☢️ 核彈級鎖碼：單一法人買超佔據當天總成交量 10% 以上！
                max_inst = max(f, it)
                if max_inst > 300 and (max_inst / v) >= 0.10:
                    inst_name = "外資" if max_inst == f else "投信"
                    nuke_list.append(f"☢️ {sid} {info['name']} | {inst_name}霸道狂掃 {max_inst}張 (佔總量 {round((max_inst/v)*100, 1)}%)")

                # 🩸 踩著屍體上漲：法人大買 > 2000，融資斷頭/大減 > 1000
                if (f + it) > 2000 and m <= -1000:
                    slaughter_list.append(f"🩸 {sid} {info['name']} | 主力吸血 {f+it}張 / 散戶割肉 {m}張")

                # 👻 妖股甦醒：總量極低 (<3000)，但法人突然異常買超 > 300
                if v > 500 and v <= 3000 and (f > 300 or it > 300):
                    demon_list.append(f"👻 {sid} {info['name']} | 總量僅 {v}張 / 異動買盤 {max(f, it)}張")

            # --- 激進戰報輸出 ---
            msg = f"🐺【血犬系統 PRO｜終極籌碼暴力】\n📅 獵殺日: {date_str}\n\n"
            
            msg += "☢️【核彈鎖碼區】(買盤佔總量>10%)\n" + "━"*20 + "\n"
            msg += "\n".join(nuke_list) if nuke_list else "今日無核彈級異動"
            msg += "\n\n"
            
            msg += "🩸【血腥屠殺區】(主力狂買+散戶大退)\n" + "━"*20 + "\n"
            msg += "\n".join(slaughter_list) if slaughter_list else "今日無明顯割肉潮"
            msg += "\n\n"
            
            msg += "👻【妖股甦醒區】(冷門股異常資金進駐)\n" + "━"*20 + "\n"
            msg += "\n".join(demon_list) if demon_list else "今日無妖氣"
            
            self.send_telegram(msg)
            print("✅ 獵殺報告已發送。")

        except Exception as e:
            self.send_telegram(f"⚠️ 系統崩潰:\n{str(e)}\n{traceback.format_exc()[:300]}")

if __name__ == "__main__":
    hound = Bloodhound()
    hound.hunt()
