import requests
import pandas as pd
from datetime import datetime

TELEGRAM_TOKEN = "8885153743:AAEjhEazpexj2j-Az-UzaOQWBy4mN145KMY"
CHAT_ID = "8543567603"

def get_taiwan_stock_data():
    print("龍蝦正在潛入深海，全市場地毯式掃描大戶籌碼...")
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 1. 抓取法人數據
        url_inst = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockHoldingLogs&data_id=all&start_date={today}"
        resp_inst = requests.get(url_inst).json()
        
        # 2. 抓取股價與成交量
        url_price = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&data_id=all&start_date={today}"
        resp_price = requests.get(url_price).json()
        
        if not resp_inst.get('data') or not resp_price.get('data'):
            return "⚠️ 報告：今日盤後資料尚未更新，或證交所休市中。"
            
        df_inst = pd.DataFrame(resp_inst['data'])
        df_price = pd.DataFrame(resp_price['data'])
        
        # 3. 解析投信(SITC)與外資(Foreign_Investor)
        df_sitc = df_inst[df_inst['institutional_investor'] == 'SITC'].copy()
        df_foreign = df_inst[df_inst['institutional_investor'] == 'Foreign_Investor'].copy()
        
        # 計算淨買超並轉換格式
        for df in [df_sitc, df_foreign]:
            df['buy'] = pd.to_numeric(df['buy'], errors='coerce').fillna(0)
            df['sell'] = pd.to_numeric(df['sell'], errors='coerce').fillna(0)
            df['net_buy'] = df['buy'] - df['sell']
            
        # 4. 彙整數據
        df_sitc = df_sitc[['stock_id', 'net_buy']].rename(columns={'net_buy': 'sitc_net'})
        df_foreign = df_foreign[['stock_id', 'net_buy']].rename(columns={'net_buy': 'foreign_net'})
        
        # 合併股價與成交量
        df_price['Trading_Volume'] = pd.to_numeric(df_price['Trading_Volume'], errors='coerce').fillna(0)
        df_price['close'] = pd.to_numeric(df_price['close'], errors='coerce').fillna(0)
        
        df_total = pd.merge(df_price[['stock_id', 'close', 'Trading_Volume']], df_sitc, on='stock_id', how='left').fillna(0)
        df_total = pd.merge(df_total, df_foreign, on='stock_id', how='left').fillna(0)
        
        # 5. 無情過濾：基本流動性門檻（成交量大於 1,000 張）
        df_filter = df_total[df_total['Trading_Volume'] > 1000].copy()
        
        # 計算大戶買超佔成交量比例
        df_filter['sitc_ratio'] = df_filter['sitc_net'] / df_filter['Trading_Volume']
        df_filter['foreign_ratio'] = df_filter['foreign_net'] / df_filter['Trading_Volume']
        
        # 分類邏輯
        # 投信鎖碼標準：投信買超佔比 > 5%
        # 外資狙擊標準：外資買超佔比 > 8% 
        sitc_leak = (df_filter['sitc_ratio'] > 0.05) & (df_filter['foreign_ratio'] <= 0.08)
        foreign_leak = (df_filter['foreign_ratio'] > 0.08) & (df_filter['sitc_ratio'] <= 0.05)
        both_leak = (df_filter['sitc_ratio'] > 0.04) & (df_filter['foreign_ratio'] > 0.04) 
        
        report = f"🦞 【無情龍蝦每日籌碼獵殺報告】\n日期：{today}\n全市場掃描結果：\n\n"
        
        # --- 分類一：土洋大戶聯手抬轎股 ---
        report += "🔥 【第一類：土洋聯手抬轎暴利股】\n"
        df_both = df_filter[both_leak]
        if df_both.empty: report += ">> 今日暫無標的。\n"
        for _, row in df_both.iterrows():
            report += f"🎯 股票：{row['stock_id']} | 價：{row['close']} 元\n"
            report += f"   量：{int(row['Trading_Volume']):,}張\n"
            report += f"   投信買：{int(row['sitc_net']):,}張 | 外資買：{int(row['foreign_net']):,}張\n"
            
        # --- 分類二：投信獨門鎖碼股 ---
        report += "\n📈 【第二類：投信獨門強力鎖碼股】\n"
        df_sitc_only = df_filter[sitc_leak]
        if df_sitc_only.empty: report += ">> 今日暫無標的。\n"
        for _, row in df_sitc_only.iterrows():
            report += f"🎯 股票：{row['stock_id']} | 價：{row['close']} 元\n"
            report += f"   量：{int(row['Trading_Volume']):,}張\n"
            report += f"   投信強啃：{int(row['sitc_net']):,}張 (佔比 {row['sitc_ratio']*100:.1f}%)\n"
            
        # --- 分點三：外資重倉狙擊股 ---
        report += "\n💎 【第三類：外資重倉大戶狙擊股】\n"
        df_foreign_only = df_filter[foreign_leak]
        if df_foreign_only.empty: report += ">> 今日暫無標的。\n"
        for _, row in df_foreign_only.iterrows():
            report += f"🎯 股票：{row['stock_id']} | 價：{row['close']} 元\n"
            report += f"   量：{int(row['Trading_Volume']):,}張\n"
            report += f"   外資狂吞：{int(row['foreign_net']):,}張 (佔比 {row['foreign_ratio']*100:.1f}%)\n"
            
        report += "\n🚫 龍蝦防禦底線：破5日線即刻停損，不抱一絲幻想。"
        return report

    except Exception as e:
        return f"❌ 龍蝦大腦出錯，原因：{str(e)}"

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, json=payload)

if __name__ == "__main__":
    result_report = get_taiwan_stock_data()
    send_telegram_msg(result_report)
