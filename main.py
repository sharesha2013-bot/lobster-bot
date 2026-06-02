# ==========================================
# 🦅 不死鳥濾網 (靈敏度微調 + 除錯雷達)
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
            
        today_vol = df['Volume'].iloc[-1]
        prev_5d_vol_avg = df['Volume'].iloc[-6:-1].mean()
        
        today_close = df['Close'].iloc[-1]
        yesterday_close = df['Close'].iloc[-2]
        pct_change = ((today_close - yesterday_close) / yesterday_close) * 100
        
        # 🚨【大俠專屬除錯雷達】：直接把群創的底牌印在你的電腦畫面上
        if stock_id == '3481':
            print(f"🦞【系統監測 3481 群創】")
            print(f"今日成交量: {today_vol}")
            print(f"五日均量: {prev_5d_vol_avg}")
            print(f"今日漲跌幅: {pct_change:.2f}%")
        
        # 防呆：避免除以零或無量標的
        if prev_5d_vol_avg <= 0:
            return False
            
        # 1. 爆量標準：放寬至 1.5 倍以上即可 (避免 Yahoo 數據誤差)
        # 2. 滯跌標準：跌幅小於 1.5% (即漲跌幅 >= -1.5%)
        if today_vol >= (prev_5d_vol_avg * 1.5) and pct_change >= -1.5:
            return True
            
        return False
    except Exception as e:
        # 如果發生錯誤，把錯誤原因印出來
        if stock_id == '3481': 
            print(f"⚠️ 3481 濾網運算錯誤: {e}")
        return False
