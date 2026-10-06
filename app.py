import os
import glob
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------
# ページ基本設定
# ---------------------------------------------------------
st.set_page_config(
    page_title="株式スクリーナー & ウォッチリスト管理",
    page_icon="📈",
    layout="wide"
)

st.title("📈 株式スクリーナー & ウォッチリスト管理")
st.caption("自動スクリーニング結果、マイウォッチリスト管理、個別銘柄分析、仮想運用シミュレーション")

# ---------------------------------------------------------
# セッション状態（ウォッチリストの保持）の初期化
# ---------------------------------------------------------
if "watchlist" not in st.session_state:
    # 初期サンプル登録（トヨタ、ソニー、NTT）
    st.session_state.watchlist = [
        {"Ticker": "7203.T", "銘柄名": "トヨタ自動車", "メモ": "主力・高配当"},
        {"Ticker": "6758.T", "銘柄名": "ソニーグループ", "メモ": "エンタメ・半導体"},
        {"Ticker": "9432.T", "銘柄名": "NTT", "メモ": "ディフェンシブ"}
    ]

# ---------------------------------------------------------
# サイドバー：共通データ読み込み & 設定
# ---------------------------------------------------------
st.sidebar.header("📁 データ & 設定")

csv_files = glob.glob("results/*.csv")

if csv_files:
    selected_file = st.sidebar.selectbox("データファイルの選択", sorted(csv_files, reverse=True))
    try:
        df_raw = pd.read_csv(selected_file)
        st.sidebar.success(f"ファイルを読み込みました: {os.path.basename(selected_file)}")
    except Exception as e:
        st.sidebar.error(f"ファイルの読み込みに失敗しました: {e}")
        df_raw = pd.DataFrame()
else:
    st.sidebar.warning("`results/` フォルダ内にCSVファイルが見つかりません。サンプルデータで表示します。")
    df_raw = pd.DataFrame({
        "Ticker": ["7203.T", "6758.T", "9432.T", "8306.T", "6861.T"],
        "銘柄名": ["トヨタ自動車", "ソニーグループ", "NTT", "三菱UFJ", "キーエンス"],
        "株価": [2650, 13200, 155, 1580, 68000],
        "PER": [9.8, 16.5, 11.2, 10.4, 38.2],
        "PBR": [1.02, 2.10, 1.25, 0.85, 4.15],
        "RSI": [42.5, 58.0, 35.1, 62.4, 48.9],
        "判定": ["買い条件合致", "買い条件合致", "監視対象", "買い条件合致", "監視対象"]
    })

# ---------------------------------------------------------
# メインタブの構成（4つのタブ）
# ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 スクリーニング対象銘柄一覧",
    "⭐ マイ・ウォッチリスト",
    "🔍 個別銘柄 詳細分析 (yfinance)",
    "📊 デモ取引シミュレーション"
])

# =========================================================
# タブ1: スクリーニング結果データテーブル表示
# =========================================================
with tab1:
    st.subheader("📋 本日の自動スクリーニング推奨銘柄")
    if not df_raw.empty:
        if "判定" in df_raw.columns:
            status_list = ["すべて"] + list(df_raw["判定"].unique())
            selected_status = st.selectbox("判定ステータスで絞り込み", status_list)
            if selected_status != "すべて":
                filtered_df = df_raw[df_raw["判定"] == selected_status]
            else:
                filtered_df = df_raw
        else:
            filtered_df = df_raw
            
        st.dataframe(filtered_df, use_container_width=True)
        st.caption(f"該当銘柄数: {len(filtered_df)} 件")
    else:
        st.warning("表示できるデータがありません。")

# =========================================================
# タブ2: マイ・ウォッチリスト（追加・削除機能）
# =========================================================
with tab2:
    st.subheader("⭐ マイ・ウォッチリスト管理")
    st.caption("気になる銘柄を手動で追加・削除して管理できます。")

    # 新規追加フォーム
    with st.form("add_symbol_form", clear_on_submit=True):
        st.markdown("##### ➕ 新しい銘柄を登録")
        col_a, col_b, col_c, col_d = st.columns([2, 3, 4, 2])
        with col_a:
            new_ticker = st.text_input("銘柄コード (例: 9984.T)", placeholder="9984.T")
        with col_b:
            new_name = st.text_input("銘柄名 (例: ソフトバンクG)", placeholder="ソフトバンクG")
        with col_c:
            new_memo = st.text_input("メモ (例: AI関連・決算前)", placeholder="メモを入力")
        with col_d:
            st.write("") # スペース調整
            st.write("")
            submit_btn = st.form_submit_button("リストに追加")

        if submit_btn:
            if new_ticker:
                # 重複チェック
                existing_tickers = [item["Ticker"] for item in st.session_state.watchlist]
                if new_ticker.upper() in existing_tickers:
                    st.error(f"{new_ticker} は既にリストに存在します。")
                else:
                    st.session_state.watchlist.append({
                        "Ticker": new_ticker.upper(),
                        "銘柄名": new_name if new_name else new_ticker.upper(),
                        "メモ": new_memo if new_memo else "-"
                    })
                    st.success(f"銘柄【{new_ticker.upper()}】をウォッチリストに追加しました！")
                    st.rerun()
            else:
                st.warning("銘柄コードを入力してください。")

    st.markdown("---")

    # リスト一覧・削除機能
    st.markdown("##### 📄 現在のウォッチリスト一覧")
    if st.session_state.watchlist:
        df_watch = pd.DataFrame(st.session_state.watchlist)
        
        # 1銘柄ずつ削除ボタン付きで表示
        for idx, item in enumerate(st.session_state.watchlist):
            c_code, c_name, c_memo, c_del = st.columns([2, 3, 4, 2])
            with c_code:
                st.markdown(f"**`{item['Ticker']}`**")
            with c_name:
                st.write(item["銘柄名"])
            with c_memo:
                st.write(f"📝 {item['メモ']}")
            with c_del:
                if st.button("🗑️ 削除", key=f"del_{idx}"):
                    st.session_state.watchlist.pop(idx)
                    st.success(f"削除しました: {item['Ticker']}")
                    st.rerun()
            st.markdown("<hr style='margin: 4px 0;'>", unsafe_allow_html=True)
    else:
        st.info("現在ウォッチリストに登録されている銘柄はありません。上のフォームから追加してください。")

# =========================================================
# タブ3: 個別銘柄 詳細分析 (yfinance)
# =========================================================
with tab3:
    st.subheader("🔍 個別銘柄のリアルタイム分析")
    
    # スクリーニング推奨銘柄とウォッチリストの両方を統合した選択肢リストを作成
    combined_options = []
    
    # 1. ウォッチリストから選択肢を作成
    if st.session_state.watchlist:
        for item in st.session_state.watchlist:
            combined_options.append(f"⭐ [ウォッチ] {item['Ticker']} - {item['銘柄名']}")
            
    # 2. スクリーニング一覧から選択肢を作成
    if not df_raw.empty and "Ticker" in df_raw.columns:
        for _, row in df_raw.iterrows():
            name = row.get("銘柄名", row["Ticker"])
            opt = f"📋 [推奨] {row['Ticker']} - {name}"
            if opt not in combined_options:
                combined_options.append(opt)
    
    if combined_options:
        selected_option = st.selectbox("分析する銘柄を選択してください", combined_options)
        # コードだけを抽出（例: "⭐ [ウォッチ] 7203.T - トヨタ" -> "7203.T"）
        selected_ticker = selected_option.split("] ")[1].split(" - ")[0]
    else:
        selected_ticker = st.text_input("銘柄コードを入力 (例: 7203.T)", value="7203.T")
    
    period = st.radio("表示期間", ["1mo", "3mo", "6mo", "1y"], index=2, horizontal=True)
    
    if selected_ticker:
        with st.spinner(f"{selected_ticker} の株価データを取得中..."):
            try:
                stock = yf.Ticker(selected_ticker)
                hist = stock.history(period=period)
                info = stock.info
                
                if not hist.empty:
                    latest_close = hist["Close"].iloc[-1]
                    prev_close = hist["Close"].iloc[-2] if len(hist) > 1 else latest_close
                    change = latest_close - prev_close
                    change_pct = (change / prev_close) * 100
                    
                    company_name = info.get("longName", info.get("shortName", selected_ticker))
                    
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("選択中の銘柄", company_name)
                    with c2:
                        st.metric("最新終値", f"¥{latest_close:,.1f}", f"{change:+.1f} ({change_pct:+.2f}%)")
                    with c3:
                        market_cap = info.get("marketCap", 0)
                        st.metric("時価総額", f"¥{market_cap/1e8:,.0f} 億円" if market_cap else "N/A")
                    
                    # 移動平均線
                    hist["SMA20"] = hist["Close"].rolling(window=20).mean()
                    hist["SMA50"] = hist["Close"].rolling(window=50).mean()
                    
                    # ローソク足チャート
                    fig_stock = go.Figure()
                    fig_stock.add_trace(go.Candlestick(
                        x=hist.index, open=hist["Open"], high=hist["High"],
                        low=hist["Low"], close=hist["Close"], name="株価"
                    ))
                    fig_stock.add_trace(go.Scatter(x=hist.index, y=hist["SMA20"], mode='lines', name='20日移動平均', line=dict(color='orange', width=1.5)))
                    fig_stock.add_trace(go.Scatter(x=hist.index, y=hist["SMA50"], mode='lines', name='50日移動平均', line=dict(color='blue', width=1.5)))
                    
                    fig_stock.update_layout(
                        title=f"{selected_ticker} の株価・移動平均線チャート",
                        yaxis_title="株価 (JPY)", xaxis_rangeslider_visible=False,
                        height=480, hovermode="x unified"
                    )
                    st.plotly_chart(fig_stock, use_container_width=True)
                else:
                    st.error(f"{selected_ticker} のデータが見つかりませんでした。")
            except Exception as e:
                st.error(f"データ取得中にエラーが発生しました: {e}")

# =========================================================
# タブ4: デモ取引シミュレーション
# =========================================================
with tab4:
    st.subheader("💡 仮想トレード・パラメータ設定")
    
    col_param1, col_param2, col_param3, col_param4 = st.columns(4)
    
    with col_param1:
        initial_capital = st.number_input(
            "初期投資金額 (JPY)",
            min_value=100_000, max_value=10_000_000, value=1_000_000, step=100_000
        )
    with col_param2:
        take_profit_pct = st.slider(
            "目標利確ライン (Take Profit %)",
            min_value=1.0, max_value=20.0, value=5.0, step=0.5
        ) / 100.0
    with col_param3:
        stop_loss_pct = st.slider(
            "損切りライン (Stop Loss %)",
            min_value=1.0, max_value=15.0, value=3.0, step=0.5
        ) / 100.0
    with col_param4:
        simulation_days = st.slider(
            "検証期間 (営業日)",
            min_value=10, max_value=90, value=30, step=5
        )

    # --- 計算ロジック ---
    np.random.seed(42)
    daily_returns_strategy = np.random.normal(0.0035, 0.012, simulation_days)
    daily_returns_benchmark = np.random.normal(0.0005, 0.008, simulation_days)
    daily_returns_strategy = np.clip(daily_returns_strategy, -stop_loss_pct, take_profit_pct)

    portfolio_values = initial_capital * np.cumprod(1 + daily_returns_strategy)
    portfolio_values = np.insert(portfolio_values, 0, initial_capital)

    benchmark_values = initial_capital * np.cumprod(1 + daily_returns_benchmark)
    benchmark_values = np.insert(benchmark_values, 0, initial_capital)

    final_value = portfolio_values[-1]
    total_return_pct = ((final_value - initial_capital) / initial_capital) * 100

    trades = daily_returns_strategy[daily_returns_strategy != 0]
    win_trades = trades[trades > 0]
    loss_trades = trades[trades < 0]

    win_count = len(win_trades)
    loss_count = len(loss_trades)
    total_trades = win_count + loss_count
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

    total_profit = np.sum(win_trades) if win_count > 0 else 0
    total_loss = np.abs(np.sum(loss_trades)) if loss_count > 0 else 1e-6
    profit_factor = total_profit / total_loss

    st.markdown("---")

    # --- KPIカード表示 ---
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("最終資産額", f"¥{final_value:,.0f}", f"{total_return_pct:+.1f}%")
    with kpi2:
        st.metric("勝率", f"{win_rate:.1f}%", f"{win_count}勝 {loss_count}敗", delta_color="off")
    with kpi3:
        pf_status = "優良 (>1.5)" if profit_factor >= 1.5 else "要改善 (<1.5)"
        st.metric("プロフィットファクター", f"{profit_factor:.2f}", pf_status, delta_color="normal" if profit_factor >= 1.5 else "inverse")
    with kpi4:
        st.metric("総取引数", f"{total_trades} 回", f"期間: {simulation_days}営業日", delta_color="off")

    st.markdown("---")

    # --- 資産推移チャート ---
    st.subheader("📊 資産推移・ベンチマーク比較チャート")
    days_label = [f"{i}日目" for i in range(simulation_days + 1)]

    fig_sim = go.Figure()
    fig_sim.add_trace(go.Scatter(
        x=days_label, y=portfolio_values, mode='lines+markers', name='デモ戦略ポートフォリオ',
        line=dict(color='#2563EB', width=3), fill='tonexty', fillcolor='rgba(37, 99, 235, 0.08)'
    ))
    fig_sim.add_trace(go.Scatter(
        x=days_label, y=benchmark_values, mode='lines+markers', name='ベンチマーク (TOPIX相当)',
        line=dict(color='#64748B', width=2, dash='dot')
    ))
    fig_sim.update_layout(
        xaxis_title="経過日数", yaxis_title="資産額 (JPY)", yaxis=dict(tickformat=",.0f"),
        hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=40, b=20), height=420
    )
    st.plotly_chart(fig_sim, use_container_width=True)
