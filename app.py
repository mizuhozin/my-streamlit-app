import os
import glob
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import streamlit as st

# ページ基本設定
st.set_page_config(
    page_title="株式スクリーナー & 個別銘柄分析ダッシュボード",
    page_icon="📈",
    layout="wide"
)

st.title("📈 株式スクリーナー & 個別銘柄分析ダッシュボード")
st.caption("日次スクリーニング結果の確認および個別銘柄の株価・テクニカル分析")

# --- 1. データファイルの読み込み ---
st.sidebar.header("📁 データ選択")

csv_files = glob.glob("results/*.csv")

if csv_files:
    selected_file = st.sidebar.selectbox("スクリーニング結果データ", sorted(csv_files, reverse=True))
    try:
        df_screener = pd.read_csv(selected_file)
        st.sidebar.success(f"読み込み完了: {os.path.basename(selected_file)}")
    except Exception as e:
        st.sidebar.error(f"ファイル読み込みエラー: {e}")
        df_screener = pd.DataFrame()
else:
    st.sidebar.info("💡 `results/` にCSVがないため、サンプル銘柄を表示します。")
    # テスト用サンプルデータ
    df_screener = pd.DataFrame({
        "Ticker": ["7203.T", "6758.T", "9432.T", "8306.T", "6861.T"],
        "銘柄名": ["トヨタ自動車", "ソニーグループ", "NTT", "三菱UFJ", "キーエンス"],
        "株価": [2650, 13200, 155, 1580, 68000],
        "PER": [9.8, 16.5, 11.2, 10.4, 38.2],
        "PBR": [1.02, 2.10, 1.25, 0.85, 4.15],
        "RSI": [42.5, 58.0, 35.1, 62.4, 48.9],
        "判定": ["買い条件合致", "買い条件合致", "監視対象", "買い条件合致", "監視対象"]
    })

# --- 2. メインタブ切り替え ---
tab1, tab2 = st.tabs(["📋 スクリーニング結果一覧", "🔍 個別銘柄 詳細分析"])

# ==========================================
# タブ1: スクリーニング結果一覧
# ==========================================
with tab1:
    st.subheader("📋 本日のスクリーニング対象銘柄")
    
    if not df_screener.empty:
        # フィルター機能
        if "判定" in df_screener.columns:
            status_list = ["すべて"] + list(df_screener["判定"].unique())
            selected_status = st.selectbox("判定ステータスで絞り込み", status_list)
            if selected_status != "すべて":
                filtered_df = df_screener[df_screener["判定"] == selected_status]
            else:
                filtered_df = df_screener
        else:
            filtered_df = df_screener
            
        st.dataframe(filtered_df, use_container_width=True)
        
        col_stat1, col_stat2 = st.columns(2)
        with col_stat1:
            st.metric("検出銘柄数", f"{len(filtered_df)} 件")
    else:
        st.warning("表示できる銘柄データがありません。")

# ==========================================
# タブ2: 個別銘柄 詳細分析
# ==========================================
with tab2:
    st.subheader("🔍 個別銘柄のリアルタイム分析 (yfinanceデータ)")
    
    # 銘柄選択用のドロップダウンを作成
    if not df_screener.empty and "Ticker" in df_screener.columns:
        # 銘柄コードと名前を結合したリストを作成
        if "銘柄名" in df_screener.columns:
            symbol_options = [f"{row['Ticker']} - {row['銘柄名']}" for _, row in df_screener.iterrows()]
        else:
            symbol_options = list(df_screener["Ticker"])
        
        selected_option = st.selectbox("分析する銘柄を選択してください", symbol_options)
        selected_ticker = selected_option.split(" - ")[0]
    else:
        selected_ticker = st.text_input("銘柄コードを入力（例: 7203.T）", value="7203.T")
    
    # 期間選択
    period = st.radio("表示期間", ["1mo", "3mo", "6mo", "1y"], index=2, horizontal=True)
    
    if selected_ticker:
        with st.spinner(f"{selected_ticker} の最新株価データを取得中..."):
            try:
                stock = yf.Ticker(selected_ticker)
                hist = stock.history(period=period)
                info = stock.info
                
                if not hist.empty:
                    # 最新値の取得
                    latest_close = hist["Close"].iloc[-1]
                    prev_close = hist["Close"].iloc[-2] if len(hist) > 1 else latest_close
                    change = latest_close - prev_close
                    change_pct = (change / prev_close) * 100
                    
                    # 企業基本情報カード
                    company_name = info.get("longName", info.get("shortName", selected_ticker))
                    col_info1, col_info2, col_info3 = st.columns(3)
                    
                    with col_info1:
                        st.metric("選択中の銘柄", company_name)
                    with col_info2:
                        st.metric("最新終値", f"¥{latest_close:,.1f}", f"{change:+.1f} ({change_pct:+.2f}%)")
                    with col_info3:
                        market_cap = info.get("marketCap", 0)
                        st.metric("時価総額", f"¥{market_cap/1e8:,.0f} 億円" if market_cap else "N/A")
                    
                    # 移動平均線の計算
                    hist["SMA20"] = hist["Close"].rolling(window=20).mean()
                    hist["SMA50"] = hist["Close"].rolling(window=50).mean()
                    
                    # ローソク足 & 移動平均線 チャート (Plotly)
                    fig = go.Figure()
                    
                    # ローソク足
                    fig.add_trace(go.Candlestick(
                        x=hist.index,
                        open=hist["Open"],
                        high=hist["High"],
                        low=hist["Low"],
                        close=hist["Close"],
                        name="株価 (ローソク足)"
                    ))
                    
                    # 移動平均線 (20日 & 50日)
                    fig.add_trace(go.Scatter(x=hist.index, y=hist["SMA20"], mode='lines', name='20日移動平均', line=dict(color='orange', width=1.5)))
                    fig.add_trace(go.Scatter(x=hist.index, y=hist["SMA50"], mode='lines', name='50日移動平均', line=dict(color='blue', width=1.5)))
                    
                    fig.update_layout(
                        title=f"{selected_ticker} 株価チャート",
                        yaxis_title="株価 (JPY)",
                        xaxis_rangeslider_visible=False,
                        height=500,
                        hovermode="x unified"
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 過去データのテーブル表示
                    with st.expander("📄 過去株価データの詳細を表示"):
                        st.dataframe(hist.sort_index(ascending=False), use_container_width=True)
                        
                else:
                    st.error(f"{selected_ticker} の株価データが見つかりませんでした。")
            except Exception as e:
                st.error(f"データ取得中にエラーが発生しました: {e}")
