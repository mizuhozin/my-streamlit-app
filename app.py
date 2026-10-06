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
    page_title="株式スクリーナー & ウォッチリスト・運用分析",
    page_icon="📈",
    layout="wide"
)

st.title("📈 株式スクリーナー & ウォッチリスト・運用分析")
st.caption("自動スクリーニング、ポートフォリオ管理、個別銘柄チャート、実銘柄/仮想取引シミュレーション")

# ---------------------------------------------------------
# セッション状態（保有銘柄・ウォッチリスト）の初期化
# ---------------------------------------------------------
if "watchlist" not in st.session_state:
    st.session_state.watchlist = [
        {"Ticker": "2914.T", "銘柄名": "日本JT", "メモ": "保有: 10株 / 超高配当・ディフェンシブ"},
        {"Ticker": "8001.T", "銘柄名": "伊藤忠商事", "メモ": "保有: 5株 / 総合商社・非資源強み"},
        {"Ticker": "8058.T", "銘柄名": "三菱商事", "メモ": "保有: 5株 / 総合商社・連続増配"},
        {"Ticker": "8316.T", "銘柄名": "三井住友FG", "メモ": "保有: 10株 / メガバンク・高配当"},
        {"Ticker": "8593.T", "銘柄名": "三菱HCキャピタル", "メモ": "保有: 10株 / 20期以上連続増配"},
        {"Ticker": "8697.T", "銘柄名": "日本取引所グループ", "メモ": "保有: 5株 / 東証運営・インフラ独占"},
        {"Ticker": "8725.T", "銘柄名": "MS&ADインシュアランスG", "メモ": "保有: 5株 / 損保大手・高配当"},
        {"Ticker": "9432.T", "銘柄名": "NTT", "メモ": "保有: 30株 / 通信ディフェンシブ"}
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
# メインタブ構成
# ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 スクリーニング対象銘柄一覧",
    "⭐ マイ・ウォッチリスト",
    "🔍 個別銘柄 詳細分析 (yfinance)",
    "📊 デモ取引・バックテストシミュレーション"
])

# =========================================================
# タブ1: スクリーニング結果
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
# タブ2: マイ・ウォッチリスト管理
# =========================================================
with tab2:
    st.subheader("⭐ マイ・ウォッチリスト管理")
    st.caption("保有銘柄や気になる銘柄を手動で追加・削除・編集できます。")

    # 新規追加フォーム
    with st.form("add_symbol_form", clear_on_submit=True):
        st.markdown("##### ➕ 新しい銘柄を登録")
        col_a, col_b, col_c, col_d = st.columns([2, 3, 4, 2])
        with col_a:
            new_ticker = st.text_input("銘柄コード (例: 9984.T)", placeholder="9984.T")
        with col_b:
            new_name = st.text_input("銘柄名 (例: ソフトバンクG)", placeholder="ソフトバンクG")
        with col_c:
            new_memo = st.text_input("メモ (例: 保有10株 / ディフェンシブ)", placeholder="メモを入力")
        with col_d:
            st.write("")
            st.write("")
            submit_btn = st.form_submit_button("リストに追加")

        if submit_btn:
            if new_ticker:
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
        st.info("現在ウォッチリストに登録されている銘柄はありません。")

# =========================================================
# タブ3: 個別銘柄 詳細分析 (yfinance)
# =========================================================
with tab3:
    st.subheader("🔍 個別銘柄のリアルタイム分析")
    
    combined_options = []
    if st.session_state.watchlist:
        for item in st.session_state.watchlist:
            combined_options.append(f"⭐ [ウォッチ] {item['Ticker']} - {item['銘柄名']}")
            
    if not df_raw.empty and "Ticker" in df_raw.columns:
        for _, row in df_raw.iterrows():
            name = row.get("銘柄名", row["Ticker"])
            opt = f"📋 [推奨] {row['Ticker']} - {name}"
            if opt not in combined_options:
                combined_options.append(opt)
    
    if combined_options:
        selected_option = st.selectbox("分析する銘柄を選択してください", combined_options, key="select_analysis_ticker")
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
                    
                    hist["SMA20"] = hist["Close"].rolling(window=20).mean()
                    hist["SMA50"] = hist["Close"].rolling(window=50).mean()
                    
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
# タブ4: デモ取引 & バックテストシミュレーション
# =========================================================
with tab4:
    st.subheader("📊 取引シミュレーション & バックテスト")
    
    # モード選択（仮想試算モデル vs 実際の銘柄データ）
    sim_mode = st.radio(
        "シミュレーション・モードの選択",
        ["🎲 仮想確率モデル (戦略全体のデモ)", "📈 実際の銘柄（過去株価データでバックテスト）"],
        horizontal=True
    )
    
    st.markdown("---")
    
    # パラメータ入力欄
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
            min_value=10, max_value=120, value=30, step=5
        )

    # ---------------------------------------------------------
    # モードA: 仮想確率モデル
    # ---------------------------------------------------------
    if sim_mode == "🎲 仮想確率モデル (戦略全体のデモ)":
        st.info("💡 確率分布モデルを用いて、戦略ルール通りの運用を行った場合の仮想的な資産推移をシミュレーションします。")
        
        np.random.seed(42)
        daily_returns_strategy = np.random.normal(0.0035, 0.012, simulation_days)
        daily_returns_benchmark = np.random.normal(0.0005, 0.008, simulation_days)
        daily_returns_strategy = np.clip(daily_returns_strategy, -stop_loss_pct, take_profit_pct)

        portfolio_values = initial_capital * np.cumprod(1 + daily_returns_strategy)
        portfolio_values = np.insert(portfolio_values, 0, initial_capital)

        benchmark_values = initial_capital * np.cumprod(1 + daily_returns_benchmark)
        benchmark_values = np.insert(benchmark_values, 0, initial_capital)

        labels = [f"{i}日目" for i in range(simulation_days + 1)]
        target_name = "仮想戦略ポートフォリオ"

    # ---------------------------------------------------------
    # モードB: 実際の銘柄データでバックテスト
    # ---------------------------------------------------------
    else:
        st.info("💡 ウォッチリストまたはスクリーニング結果から実銘柄を選び、実際の過去株価データに基づいてバックテストを行います。")
        
        # 銘柄選択肢を作成
        sim_ticker_options = []
        if st.session_state.watchlist:
            for item in st.session_state.watchlist:
                sim_ticker_options.append(f"⭐ [ウォッチ] {item['Ticker']} - {item['銘柄名']}")
        if not df_raw.empty and "Ticker" in df_raw.columns:
            for _, row in df_raw.iterrows():
                name = row.get("銘柄名", row["Ticker"])
                opt = f"📋 [推奨] {row['Ticker']} - {name}"
                if opt not in sim_ticker_options:
                    sim_ticker_options.append(opt)

        if sim_ticker_options:
            selected_sim_opt = st.selectbox("シミュレーション対象の銘柄を選択", sim_ticker_options, key="sim_ticker_select")
            target_ticker = selected_sim_opt.split("] ")[1].split(" - ")[0]
            target_name = selected_sim_opt.split(" - ")[1]
        else:
            target_ticker = "7203.T"
            target_name = "トヨタ自動車"

        # yfinance から実データ取得
        with st.spinner(f"{target_ticker} の過去株価データを取得して検証中..."):
            stock_sim = yf.Ticker(target_ticker)
            # 余裕をもって多めに取得
            hist_sim = stock_sim.history(period="6mo")

        if not hist_sim.empty and len(hist_sim) >= simulation_days:
            # 最新から指定営業日数分を切り出し
            sub_hist = hist_sim.tail(simulation_days + 1)
            prices = sub_hist["Close"].values
            
            # 日次変化率
            daily_changes = np.diff(prices) / prices[:-1]
            
            # 利確・損切りルールの適用
            clipped_changes = np.clip(daily_changes, -stop_loss_pct, take_profit_pct)
            
            # 資産推移計算
            portfolio_values = initial_capital * np.cumprod(1 + clipped_changes)
            portfolio_values = np.insert(portfolio_values, 0, initial_capital)
            
            # 単純保有（ホールド）した場合の比較
            hold_returns = daily_changes
            benchmark_values = initial_capital * np.cumprod(1 + hold_returns)
            benchmark_values = np.insert(benchmark_values, 0, initial_capital)
            
            labels = [d.strftime('%m/%d') for d in sub_hist.index]
            daily_returns_strategy = clipped_changes
        else:
            st.error("株価データの取得件数が不足しています。他の期間または銘柄をお試しください。")
            st.stop()

    # --- KPI計算・表示（共通） ---
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

    # --- チャート表示 ---
    st.subheader(f"📊 {target_name} 資産推移・バックテストチャート")

    fig_sim = go.Figure()
    fig_sim.add_trace(go.Scatter(
        x=labels, y=portfolio_values, mode='lines+markers', name='ルール適用時の運用推移',
        line=dict(color='#2563EB', width=3), fill='tonexty', fillcolor='rgba(37, 99, 235, 0.08)'
    ))
    fig_sim.add_trace(go.Scatter(
        x=labels, y=benchmark_values, mode='lines+markers',
        name='そのまま保有(ホールド)の場合' if sim_mode != "🎲 仮想確率モデル (戦略全体のデモ)" else 'ベンチマーク (TOPIX相当)',
        line=dict(color='#64748B', width=2, dash='dot')
    ))
    fig_sim.update_layout(
        xaxis_title="日付 / 経過日数", yaxis_title="資産額 (JPY)", yaxis=dict(tickformat=",.0f"),
        hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=40, b=20), height=420
    )
    st.plotly_chart(fig_sim, use_container_width=True)
