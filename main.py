# 必要なライブラリのインポート
import yfinance as yf
from curl_cffi import requests

# yfinanceが内部で使うrequestsセッションをcurl_cffiに置き換える
yf.ticker._requests = requests.Session()

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from datetime import datetime
import warnings

# 警告を抑制（必要に応じて）
warnings.filterwarnings('ignore', category=FutureWarning)

# セクターETFのシンボルリスト
sector_etfs = ["XLK", "XLY", "XLV", "XLP", "XLB", "XLU", "XLI", "XLC", "XLRE", "XLF", "XLE", "BIZD", "TLT", "SPY", "SOXX", "QQQ", "GLD", "JEPI", "SHY", "XME", "LQD", "IEF"]

# すべてのデータを1つのDataFrameに収集する
def get_all_data(etfs, period='1y'):
    try:
        # Download all tickers at once
        data = yf.download(
            tickers=etfs,
            period=period,
            progress=False,
            timeout=30,
        )

        if data.empty:
            print("Warning: yfinance.download returned an empty DataFrame.")
            return pd.DataFrame()

        # Extract 'Adj Close' and 'Close' data.
        # The result of yf.download for multiple tickers is a multi-level column DF.
        adj_close = data.get('Adj Close')
        close = data.get('Close')

        # Create a result DataFrame
        result_df = pd.DataFrame(index=data.index)

        # For each ticker, prefer 'Adj Close', but use 'Close' if it's not available or all NaN
        for ticker in etfs:
            if adj_close is not None and ticker in adj_close.columns and not adj_close[ticker].isnull().all():
                result_df[ticker] = adj_close[ticker]
            elif close is not None and ticker in close.columns and not close[ticker].isnull().all():
                print(f"{ticker}: 'Adj Close' データが取得できませんでした。代わりに 'Close' を使用します。")
                result_df[ticker] = close[ticker]
            else:
                print(f"{ticker}: 価格データが取得できませんでした。")

        if result_df.empty:
            print("Error: Could not construct a valid DataFrame from downloaded data.")

        return result_df.dropna(how='all') # Drop rows that are all NaN

    except Exception as e:
        print(f"An error occurred in get_all_data: {str(e)}")
        return pd.DataFrame()

# データを取得する関数
def get_data(ticker, period='1y'):
    try:
        data = yf.download(ticker, period=period, progress=False, timeout=30)
        if not data.empty:
            if 'Adj Close' in data.columns:
                return data[['Adj Close']]
            elif 'Close' in data.columns:
                return data[['Close']].rename(columns={'Close': 'Adj Close'})
        return pd.DataFrame()
    except Exception as e:
        print(f"{ticker}: データ取得エラー - {str(e)}")
        return pd.DataFrame()

# 各ETFの月次リターンを計算する
def calculate_monthly_returns(data):
    # 月末データにリサンプリングし、前月の終値で埋める
    monthly_data = data.resample('ME').ffill()
    # 前月からのパーセンテージ変化を計算
    monthly_returns = monthly_data.pct_change().dropna()
    return monthly_returns

# トレンドクラリティを計算する関数（対数株価を使用）
def calculate_trend_clarity(data):
    """
    データのトレンドクラリティを計算します（対数株価を使用）。
    
    Parameters:
    data (DataFrame): 終値と日付のデータ
    
    Returns:
    float: 傾きの符号とトレンドクラリティを掛け合わせた値
    """
    # データのコピーを作成
    data = data.copy()
    
    # 価格列の名前を取得
    price_column = 'Adj Close' if 'Adj Close' in data.columns else 'Close'
    
    # 価格データの確認
    if price_column not in data.columns:
        print(f"価格データが見つかりません。利用可能な列: {data.columns.tolist()}")
        return 0.0
    
    # ゼロや負の値を除外
    valid_data = data[data[price_column] > 0].copy()
    
    if len(valid_data) < 2:
        print("有効なデータポイントが不足しています。")
        return 0.0
    
    # 日付の数値変換（回帰分析用）
    valid_data['Day'] = np.arange(len(valid_data))
    X = valid_data['Day'].values.reshape(-1, 1)
    y = np.log(valid_data[price_column].values).reshape(-1, 1)  # 株価の対数を使用
    
    # 回帰モデルを作成
    model = LinearRegression()
    model.fit(X, y)
    y_pred = model.predict(X)
    
    # 決定係数R²を計算
    r2 = r2_score(y, y_pred)
    
    # 傾きを取得
    slope = model.coef_[0][0]
    
    # 傾きの符号とトレンドクラリティを掛け合わせる
    result = np.sign(slope) * r2
    
    return result

# XLKの各月のデータに対して、他のETFとの相関を計算し、逆数を掛ける
def calculate_weighted_clarity(base_ticker, etfs, monthly_returns, trend_clarities):
    weighted_clarities = {}
    
    # base_tickerがmonthly_returnsに存在するか確認
    if base_ticker not in monthly_returns.columns:
        print(f"{base_ticker}の月次リターンデータが見つかりません。重み付けをスキップします。")
        return trend_clarities
    
    for ticker in etfs:
        if ticker not in monthly_returns.columns:
            weighted_clarities[ticker] = trend_clarities.get(ticker, 0)
            continue
            
        # 相関を計算
        correlation = monthly_returns[base_ticker].corr(monthly_returns[ticker])
        
        # 相関がNaNでないか確認
        if pd.isna(correlation):
            weighted_clarities[ticker] = trend_clarities.get(ticker, 0)
        else:
            # 相関の逆数を計算（自己相関の場合は1を使用）
            if abs(correlation) > 0.99:  # ほぼ1の場合（自己相関）
                inverse_corr = 1.0
            elif abs(correlation) < 0.01:  # ほぼ0の場合
                inverse_corr = 100.0  # 大きな値に制限
            else:
                inverse_corr = 1 / abs(correlation)
            
            weighted_clarities[ticker] = trend_clarities.get(ticker, 0) * inverse_corr
    
    return weighted_clarities

# トレンドクラリティの計算と相関の計算を行う関数
def analyze_and_rank(etfs, periods):
    """
    各ティッカーのトレンドクラリティを計算し、期間ごとに合計してランキング付けします。
    
    Parameters:
    etfs (list): セクターETFのシンボルリスト
    periods (list): 分析する期間のリスト（例：['1mo', '2mo', '3mo', '6mo', '12mo']）
    """
    results = {ticker: {period: None for period in periods} for ticker in etfs}
    total_trend_clarity = {}

    for period in periods:
        print(f"\n期間: {period}")
        
        for ticker in etfs:
            # データを取得
            data = get_data(ticker, '1y')
            
            if data.empty:
                print(f"{ticker}: データが取得できませんでした。")
                continue
            
            # 直近の期間に対応するデータを抽出
            period_days = {
                '1mo': 21,   # 約1か月分のデータ
                '2mo': 42,   # 約2か月分のデータ
                '3mo': 63,   # 約3か月分のデータ
                '6mo': 126,  # 約6か月分のデータ
                '12mo': 252  # 約1年間のデータ
            }
            
            if period in period_days:
                data = data.iloc[-period_days[period]:]
            
            if data.empty or len(data) < 2:
                print(f"{ticker} ({period}): 十分なデータがありませんでした。")
                continue
            
            # 計算に使用したデータの期間を取得
            start_date = data.index.min().strftime('%Y-%m-%d')
            end_date = data.index.max().strftime('%Y-%m-%d')

            # 傾きの符号とトレンドクラリティを掛け合わせた値を計算
            trend_clarity = calculate_trend_clarity(data)
            results[ticker][period] = trend_clarity
            
            if ticker not in total_trend_clarity:
                total_trend_clarity[ticker] = 0
            total_trend_clarity[ticker] += trend_clarity
            
            print(f"{ticker}: トレンドクラリティ ({period}, {start_date} - {end_date}) = {trend_clarity:.3f}")
    
    # データの取得と月次リターンの計算
    print("\n月次リターンを計算中...")
    all_data = get_all_data(etfs, '1y')
    
    if all_data.empty:
        print("データを取得できませんでした。")
        return
    
    monthly_returns = calculate_monthly_returns(all_data)
    
    # XLKとの相関を考慮した合計トレンドクラリティの計算
    print("\n重み付きトレンドクラリティを計算中...")
    weighted_clarities = calculate_weighted_clarity('XLK', etfs, monthly_returns, total_trend_clarity)

    # 重み付きトレンドクラリティでランキング付け
    ranked_tickers = sorted(weighted_clarities.items(), key=lambda x: x[1], reverse=True)
    
    # 現在の日時を取得して表示
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n重み付きトレンドクラリティランキング (計算日時: {current_time}):")
    print("="*60)
    
    for rank, (ticker, weighted_clarity) in enumerate(ranked_tickers, start=1):
        # XLKとの相関を表示
        if 'XLK' in monthly_returns.columns and ticker in monthly_returns.columns:
            correlation = monthly_returns['XLK'].corr(monthly_returns[ticker])
            if not pd.isna(correlation):
                print(f"Rank {rank}: {ticker:<5} - 重み付きトレンドクラリティ = {weighted_clarity:7.3f} (XLKとの相関: {correlation:.3f})")
            else:
                print(f"Rank {rank}: {ticker:<5} - 重み付きトレンドクラリティ = {weighted_clarity:7.3f} (相関: N/A)")
        else:
            print(f"Rank {rank}: {ticker:<5} - 重み付きトレンドクラリティ = {weighted_clarity:7.3f}")

# メイン実行部分
if __name__ == "__main__":
    # 分析する期間を指定
    periods = ['1mo', '2mo', '3mo', '6mo', '12mo']
    
    # セクターETFの分析を実行
    analyze_and_rank(sector_etfs, periods)