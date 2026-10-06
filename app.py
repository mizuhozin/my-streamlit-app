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
st.caption("自動スクリーニング、ポートフォリオ管理、個別銘柄チャート、短期・中長期トレードバックテスト")

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
# サイドバー：ナビゲーションメニュー & データ読み込み
# ---------------------------------------------------------
st.sidebar.header("📌 メニュー")

menu_selection = st.sidebar.radio(
    "機能を選択してください",
    [
        "📋 スクリーニング対象銘柄一覧",
        "⭐ マイ・ウォッチリスト",
        "🔍 個別銘柄 詳細分析 (yfinance)",
        "📊 デモ取引・バックテストシミュレーション"
    ]
)

st.sidebar.markdown("---")
st.sidebar.header("📁 データ選択")

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


# =========================================================
# 画面1: 📋 スクリーニング対象銘柄一覧
# =========================================================
if menu_selection == "📋 スクリーニング対象銘柄一覧":
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

    st.markdown("---")

    st.subheader("💡 シミュレーションにおける取引ルールと評価指標の説明")
    
    col_rule1, col_rule2 = st.columns(2)
    
    with col_rule1:
        st.info("""
        **⚙️ バックテスト（ルールの運用推移）の検証条件**
        
        * **買付条件:** 対象期間の初日に初期投資資金で全額購入（エントリー）したと仮定します。
        * **目標利確ライン (Take Profit):** 1期間あたりの上昇率がこの設定値に達した場合、利益を確定してリスクをオフにします。
        * **損切りライン (Stop Loss):** 1期間あたりの下落率がこの設定値を超えた場合、損失を限定するため機械的に損切り（撤退）します。
        * **検証スパンの切り替え:**
          * **短期トレード目線:** 1日（営業日）単位での変動幅に対して利確/損切り判定を行います。
          * **中長期投資目線:** 月次（1ヶ月単位）の変動幅に対して判定を行い、ノイズを排除してトレンドを追従します。
        """)

    with col_rule2:
        st.success("""
        **📊 『ガチホ（そのまま保有）』との比較＆プロフィットファクター（PF）**
        
        * **ガチホ（そのまま保有）:** 利確や損切りを行わず、期間初日から最終日まで単純に対象銘柄を保有し続けた場合の資産推移です。
        * **プロフィットファクター (PF):**
          * 判定式: `PF = 総利益 ÷ 総損失`
          * **PF > 1.5 (優良):** 利益が損失を大きく上回っており、期待値の高い優良なトレードルールです。
          * **PF < 1.5 (要改善):** 損切りにかかる回数が多い、または利確幅が狭く、損失に対して十分な利益が得られていません。
        """)

# =========================================================
# 画面2: ⭐ マイ・ウォッチリスト管理
# =========================================================
elif menu_selection == "⭐ マイ・ウォッチリスト":
    st.subheader("⭐ マイ・ウォッチリスト管理")
    st.caption("保有銘柄や気になる銘柄を手動で追加・削除・編集できます。")

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
# 画面3: 🔍 個別銘柄 詳細分析 (yfinance)
# =========================================================
elif menu_selection == "🔍 個別銘柄 詳細分析 (yfinance)":
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
    
    period = st.radio("表示期間", ["1mo", "3mo", "6mo", "1y", "2y"], index=2, horizontal=True)
    
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
# 画面4: 📊 デモ取引・バックテストシミュレーション
# =========================================================
elif menu_selection == "📊 デモ取引・バックテストシミュレーション":
    st.subheader("📊 取引シミュレーション & バックテスト")
    
    horizon_mode = st.radio(
        "🎯 投資目線（検証スパン）の選択",
        ["⚡ 短期トレード目線 (日次スイング)", "🏛️ 中長期投資目線 (月次・トレンド重視)"],
        horizontal=True
    )
    
    st.markdown("---")
    
    col_param1, col_param2, col_param3, col_param4 = st.columns(4)
    with col_param1:
        initial_capital = st.number_input(
            "初期投資金額 (JPY)",
            min_value=100_000, max_value=10_000_000, value=1_000_000, step=100_000
        )
    with col_param2:
        take_profit_pct = st.slider(
            "目標利確ライン (Take Profit %)",
            min_value=1.0, max_value=30.0,
            value=8.0 if "短期" in horizon_mode else 15.0,
            step=0.5
        ) / 100.0
    with col_param3:
        stop_loss_pct = st.slider(
            "損切りライン (Stop Loss %)",
            min_value=1.0, max_value=15.0,
            value=3.0 if "短期" in horizon_mode else 5.0,
            step=0.5
        ) / 100.0
    with col_param4:
        if "短期" in horizon_mode:
            simulation_period = st.slider("検証期間 (営業日)", min_value=10, max_value=120, value=60, step=5)
            fetch_period = "6mo"
        else:
            simulation_period = st.slider("検証期間 (ヶ月)", min_value=3, max_value=36, value=12, step=3)
            fetch_period = "3y"

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
        selected_sim_opt = st.selectbox("シミュレーション対象銘柄", sim_ticker_options, key="sim_ticker_select_v2")
        target_ticker = selected_sim_opt.split("] ")[1].split(" - ")[0]
        target_name = selected_sim_opt.split(" - ")[1]
    else:
        target_ticker = "2914.T"
        target_name = "日本JT"

    with st.spinner(f"{target_name} ({target_ticker}) のデータを取得中..."):
        stock_sim = yf.Ticker(target_ticker)
        hist_sim = stock_sim.history(period=fetch_period)

    if not hist_sim.empty:
        if "中長期" in horizon_mode:
            # 月次データへのリサンプル（'M' から新しい仕様の 'ME' に修正）
            hist_sim = hist_sim.resample('ME').last()
            sub_hist = hist_sim.tail(simulation_period + 1)
        else:
            sub_hist = hist_sim.tail(simulation_period + 1)

        prices = sub_hist["Close"].values
        daily_changes = np.diff(prices) / prices[:-1]

        clipped_changes = np.clip(daily_changes, -stop_loss_pct, take_profit_pct)

        portfolio_values = initial_capital * np.cumprod(1 + clipped_changes)
        portfolio_values = np.insert(portfolio_values, 0, initial_capital)

        hold_returns = daily_changes
        benchmark_values = initial_capital * np.cumprod(1 + hold_returns)
        benchmark_values = np.insert(benchmark_values, 0, initial_capital)

        labels = [d.strftime('%Y/%m' if "中長期" in horizon_mode else '%m/%d') for d in sub_hist.index]
        daily_returns_strategy = clipped_changes

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

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric("最終資産額", f"¥{final_value:,.0f}", f"{total_return_pct:+.1f}%")
        with k2:
            st.metric("勝率", f"{win_rate:.1f}%", f"{win_count}勝 {loss_count}敗", delta_color="off")
        with k3:
            pf_status = "優良 (>1.5)" if profit_factor >= 1.5 else "要改善 (<1.5)"
            st.metric("プロフィットファクター", f"{profit_factor:.2f}", pf_status, delta_color="normal" if profit_factor >= 1.5 else "inverse")
        with k4:
            st.metric("検証ステップ数", f"{total_trades} 回", f"モード: {horizon_mode.split(' ')[0]}", delta_color="off")

        st.markdown("---")

        st.subheader(f"📊 {target_name} ({target_ticker}) パフォーマンス推移")
        fig_sim = go.Figure()
        fig_sim.add_trace(go.Scatter(
            x=labels, y=portfolio_values, mode='lines+markers', name='ルールの運用推移',
            line=dict(color='#2563EB', width=3), fill='tonexty', fillcolor='rgba(37, 99, 235, 0.08)'
        ))
        fig_sim.add_trace(go.Scatter(
            x=labels, y=benchmark_values, mode='lines+markers', name='ガチホ（そのまま保有）の場合',
            line=dict(color='#64748B', width=2, dash='dot')
        ))
        fig_sim.update_layout(
            xaxis_title="日付 / 経過期間", yaxis_title="資産額 (JPY)", yaxis=dict(tickformat=",.0f"),
            hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=40, b=20), height=420
        )
        st.plotly_chart(fig_sim, use_container_width=True)

        with st.expander("❓ 取引ルール・計算方式の解説を開く"):
            st.markdown("""
            * **ルールの運用推移 (青線):** 設定した「目標利確ライン」と「損切りライン」を越える変動を制限（カット）し、リスク管理を行った場合の資産推移です。
            * **ガチホ（そのまま保有） (点線):** 利確や損切りを行わずに、対象期間の最初に買ったまま保有し続けた場合の実際の株価推移（トータルリターン）です。
            * **プロフィットファクター (PF):** `総利益 ÷ 総損失` で算出され、1.5以上で「優良なトレードルール」と判定されます。
            """)
    else:
        st.error("データの取得に失敗しました。")
