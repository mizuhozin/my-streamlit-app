import glob
import os
from datetime import datetime, time, timedelta, timezone

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------------
# ページ基本設定
# ---------------------------------------------------------
st.set_page_config(
    page_title="株式スクリーナー & YTT風自動ナビ", page_icon="📈", layout="wide"
)

st.title("📈 株式スクリーナー & YTT風自動ナビ")
st.caption(
    "ダウ理論トレンド判定、YTT風自動リワード・リスク算出、分足/日足マルチ時間軸チャート、自動更新ナビ"
)

# 日本時間 (JST: UTC+9) の定義
JST = timezone(timedelta(hours=9))


# 安全なリターン（再描画）関数
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()


# ---------------------------------------------------------
# セッション状態の初期化
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
        {"Ticker": "9432.T", "銘柄名": "NTT", "メモ": "保有: 30株 / 通信ディフェンシブ"},
    ]

# 朝8:30の自動更新フラグ管理
if "last_830_refreshed_date" not in st.session_state:
    st.session_state.last_830_refreshed_date = ""


# ---------------------------------------------------------
# 日本時間ベースの取引時間判定関数（東証: 平日 9:00〜15:30）
# ---------------------------------------------------------
def is_market_open():
    now_jst = datetime.now(JST)
    if now_jst.weekday() >= 5:
        return False
    market_start = time(9, 0)
    market_end = time(15, 30)
    return market_start <= now_jst.time() <= market_end


# ---------------------------------------------------------
# 朝8:30 自動更新ロジック
# ---------------------------------------------------------
now_jst = datetime.now(JST)
today_str = now_jst.strftime("%Y-%m-%d")

# 平日かつ朝8:30〜8:31の間隔内で、まだ本日実行されていない場合にリフレッシュ
if now_jst.weekday() < 5 and now_jst.time() >= time(8, 30) and now_jst.time() < time(8, 31):
    if st.session_state.last_830_refreshed_date != today_str:
        st.session_state.last_830_refreshed_date = today_str
        safe_rerun()

# 8:30のタイミングを検知するためのバックグラウンド監視タイマー（60秒おき）
st_autorefresh(interval=60 * 1000, key="morning_830_checker")


# ---------------------------------------------------------
# サイドバー：ナビゲーション & 自動更新設定
# ---------------------------------------------------------
st.sidebar.header("📌 メニュー")

menu_selection = st.sidebar.radio(
    "機能を選択してください",
    [
        "📋 スクリーニング対象銘柄一覧",
        "⭐ マイ・ウォッチリスト",
        "🔍 個別銘柄 詳細分析 & YTTナビ",
        "📊 デモ取引・バックテストシミュレーション",
    ],
)

st.sidebar.markdown("---")
st.sidebar.header("🔄 リアルタイム自動更新設定")

auto_refresh_enabled = st.sidebar.toggle("自動更新を有効化", value=True)
refresh_minutes = st.sidebar.slider(
    "更新間隔 (分)", min_value=5, max_value=60, value=5, step=1
)

market_active = is_market_open()

if not auto_refresh_enabled:
    st.sidebar.info("⏸️ **自動更新: 手動オフ**")
elif not market_active:
    st.sidebar.warning(
        "💤 **自動更新: 取引時間外 (自動停止中)**\n※平日 9:00〜15:30 (JST) のみ稼働\n※毎朝 8:30 に日次自動更新"
    )
else:
    st.sidebar.success(f"🟢 **自動更新: 稼働中** ({refresh_minutes}分おき)")
    st_autorefresh(
        interval=refresh_minutes * 60 * 1000, key="ytt_data_refresh"
    )

# ---------------------------------------------------------
# サイドバー：🧮 資金・ポジションサイズ計算
# ---------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("🧮 資金・ポジションサイズ計算")
with st.sidebar.expander("💡 単元未満株 (楽天ミニ株) 試算", expanded=False):
    calc_price = st.number_input(
        "想定買付株価 (円)",
        min_value=1.0,
        value=2500.0,
        step=10.0,
        format="%.1f",
    )
    calc_qty = st.number_input(
        "購入株数 (1株〜)", min_value=1, value=10, step=1
    )

    calc_leverage_option = st.selectbox(
        "レバレッジ (取引区分)",
        ["1:1 (現物取引)", "1:2 (信用2倍)", "1:3.3 (信用最大)"],
        index=0,
    )
    lev_val = (
        1.0
        if "1:1" in calc_leverage_option
        else (2.0 if "1:2" in calc_leverage_option else 3.3)
    )

    total_value = calc_price * calc_qty
    required_margin = total_value / lev_val

    est_risk_pct = 0.04
    est_loss = total_value * est_risk_pct
    rec_capital = est_loss / 0.02

    st.markdown(f"**概算購入代金:** `¥{total_value:,.0f}`")
    st.markdown(f"**必要購入資金 (証拠金):** `¥{required_margin:,.0f}`")
    st.caption(
        f"※許容リスク2%/SL4%計算での推奨口座資金: **¥{rec_capital:,.0f}**"
    )

# ---------------------------------------------------------
# サイドバー：📊 ファンダメンタルズ条件（ON/OFF機能）
# ---------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("📊 ファンダメンタルフィルター")

use_per = st.sidebar.checkbox("PER (株価収益率) を考慮", value=True)
per_max = st.sidebar.number_input("PER の上限 (倍)", min_value=1.0, max_value=200.0, value=20.0, step=0.5) if use_per else None

use_pbr = st.sidebar.checkbox("PBR (株価純資産倍率) を考慮", value=True)
pbr_max = st.sidebar.number_input("PBR の上限 (倍)", min_value=0.1, max_value=50.0, value=2.0, step=0.1) if use_pbr else None

use_yield = st.sidebar.checkbox("配当利回り (%) を考慮", value=True)
yield_min = st.sidebar.number_input("配当利回りの下限 (%)", min_value=0.0, max_value=20.0, value=3.0, step=0.1) if use_yield else None

use_equity_ratio = st.sidebar.checkbox("自己資本比率 (%) を考慮", value=False)
equity_ratio_min = st.sidebar.number_input("自己資本比率の下限 (%)", min_value=0.0, max_value=100.0, value=40.0, step=5.0) if use_equity_ratio else None

use_roe = st.sidebar.checkbox("ROE (自己資本利益率 %) を考慮", value=False)
roe_min = st.sidebar.number_input("ROE の下限 (%)", min_value=0.0, max_value=100.0, value=8.0, step=0.5) if use_roe else None

# ---------------------------------------------------------
# サイドバー：📁 データ選択 & Discord通知フラグ自動分類
# ---------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("📁 データ選択")

csv_files = glob.glob("results/*.csv")

if csv_files:
    selected_file = st.sidebar.selectbox(
        "データファイルの選択", sorted(csv_files, reverse=True)
    )
    try:
        df_raw = pd.read_csv(selected_file)
        st.sidebar.success(
            f"ファイルを読み込みました: {os.path.basename(selected_file)}"
        )

        if "Discord通知" in df_raw.columns:
            df_raw["Discord通知区分"] = df_raw["Discord通知"].apply(
                lambda x: (
                    "🔔 Discord通知銘柄"
                    if str(x).strip().lower() in ["1", "true", "1.0"]
                    else "対象外"
                )
            )
        else:
            df_raw["Discord通知区分"] = [
                "🔔 Discord通知銘柄" if i < 5 else "対象外"
                for i in range(len(df_raw))
            ]

    except Exception as e:
        st.sidebar.error(f"ファイルの読み込みに失敗しました: {e}")
        df_raw = pd.DataFrame()
else:
    st.sidebar.warning(
        "`results/` フォルダ内にCSVファイルが見つかりません。サンプルデータで表示します。"
    )
    df_raw = pd.DataFrame({
        "Ticker": ["7203.T", "6758.T", "9432.T", "8306.T", "6861.T"],
        "銘柄名": [
            "トヨタ自動車",
            "ソニーグループ",
            "NTT",
            "三菱UFJ",
            "キーエンス",
        ],
        "株価": [2650, 13200, 155, 1580, 68000],
        "PER": [9.8, 16.5, 11.2, 10.4, 38.2],
        "PBR": [1.02, 2.10, 1.25, 0.85, 4.15],
        "配当利回り": [3.5, 1.2, 3.8, 3.2, 0.8],
        "自己資本比率": [38.5, 28.1, 32.0, 4.8, 95.2],
        "ROE": [11.2, 13.5, 12.1, 8.4, 11.8],
        "RSI": [42.5, 58.0, 35.1, 62.4, 48.9],
        "判定": [
            "買い条件合致",
            "買い条件合致",
            "監視対象",
            "買い条件合致",
            "監視対象",
        ],
        "Discord通知区分": [
            "🔔 Discord通知銘柄",
            "🔔 Discord通知銘柄",
            "🔔 Discord通知銘柄",
            "🔔 Discord通知銘柄",
            "🔔 Discord通知銘柄",
        ],
    })


# =========================================================
# 画面1: 📋 スクリーニング対象銘柄一覧
# =========================================================
if menu_selection == "📋 スクリーニング対象銘柄一覧":
    st.subheader("📋 本日の自動スクリーニング推奨銘柄")

    if not df_raw.empty:
        display_mode = st.radio(
            "表示範囲を選択:",
            ["🔔 Discord通知銘柄のみ（上位5件）", "📂 すべてのスクリーニング銘柄"],
            horizontal=True,
        )

        filtered_df = df_raw.copy()

        # ---------------------------------------------------------
        # ファンダメンタルズ条件のフィルタリング適用 (ONになっている項目のみ)
        # ---------------------------------------------------------
        active_conditions = []
        if use_per and "PER" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["PER"] <= per_max]
            active_conditions.append(f"PER ≤ {per_max}倍")
        if use_pbr and "PBR" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["PBR"] <= pbr_max]
            active_conditions.append(f"PBR ≤ {pbr_max}倍")
        if use_yield and "配当利回り" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["配当利回り"] >= yield_min]
            active_conditions.append(f"配当利回り ≥ {yield_min}%")
        if use_equity_ratio and "自己資本比率" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["自己資本比率"] >= equity_ratio_min]
            active_conditions.append(f"自己資本比率 ≥ {equity_ratio_min}%")
        if use_roe and "ROE" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["ROE"] >= roe_min]
            active_conditions.append(f"ROE ≥ {roe_min}%")

        if active_conditions:
            st.info(f"💡 **適用中のファンダメンタル条件:** " + " | ".join(active_conditions))
        else:
            st.caption("※ ファンダメンタルズ条件はすべて「対象外 (オフ)」になっています。")

        if "🔔 Discord通知銘柄のみ" in display_mode:
            filtered_df = filtered_df[
                filtered_df["Discord通知区分"] == "🔔 Discord通知銘柄"
            ]

        if "判定" in filtered_df.columns:
            status_list = ["すべて"] + list(filtered_df["判定"].dropna().unique())
            selected_status = st.selectbox(
                "判定ステータスでさらに絞り込み", status_list
            )
            if selected_status != "すべて":
                filtered_df = filtered_df[
                    filtered_df["判定"] == selected_status
                ]

        st.dataframe(filtered_df, use_container_width=True)
        st.caption(f"該当銘柄数: {len(filtered_df)} 件")
    else:
        st.warning("表示できるデータがありません。")

    st.markdown("---")
    st.subheader("💡 ダウ理論＆YTT風ナビの仕組み")
    col_rule1, col_rule2 = st.columns(2)
    with col_rule1:
        st.info("""
        **📈 ダウ理論に基づくトレンド判定**
        * **上昇トレンド (買い目線):** 高値と安値が切り上がっている状態。押し目買いを推奨。
        * **下降トレンド (売り目線):** 高値と安値が切り下がっている状態。戻り売り（ショート）を推奨。
        * **トレンド転換:** 直近の高値/安値を破られた場合、ポジションの解消・手仕舞いを検討します。
        """)
    with col_rule2:
        st.success("""
        **🎯 YTT風・自動SL/TP（売買両対応）設定機能**
        * **買い（ロング）の場合:** SLは「直近安値」、TPは上方目標価格。
        * **売り（ショート）の場合:** SLは「直近高値」、TPは下方目標価格。
        * **目標利確 (TP):** 設定したリスクリワード比（例: 1:1.5）に応じて全自動算出。
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
            new_ticker = st.text_input(
                "銘柄コード (例: 9984.T)", placeholder="9984.T"
            )
        with col_b:
            new_name = st.text_input(
                "銘柄名 (例: ソフトバンクG)", placeholder="ソフトバンクG"
            )
        with col_c:
            new_memo = st.text_input(
                "メモ (例: 保有10株 / ディフェンシブ)",
                placeholder="メモを入力",
            )
        with col_d:
            st.write("")
            st.write("")
            submit_btn = st.form_submit_button("リストに追加")

        if submit_btn:
            if new_ticker.strip():
                formatted_ticker = new_ticker.strip().upper()
                existing_tickers = [
                    item["Ticker"] for item in st.session_state.watchlist
                ]
                if formatted_ticker in existing_tickers:
                    st.error(f"{formatted_ticker} は既にリストに存在します。")
                else:
                    st.session_state.watchlist.append({
                        "Ticker": formatted_ticker,
                        "銘柄名": new_name.strip() if new_name.strip() else formatted_ticker,
                        "メモ": new_memo.strip() if new_memo.strip() else "-",
                    })
                    st.success(
                        f"銘柄【{formatted_ticker}】をウォッチリストに追加しました！"
                    )
                    safe_rerun()
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
                    safe_rerun()
            st.markdown("<hr style='margin: 4px 0;'>", unsafe_allow_html=True)
    else:
        st.info("現在ウォッチリストに登録されている銘柄はありません。")

# =========================================================
# 画面3: 🔍 個別銘柄 詳細分析 & YTTナビ
# =========================================================
elif menu_selection == "🔍 個別銘柄 詳細分析 & YTTナビ":
    st.subheader("🔍 個別銘柄 詳細分析 & YTT風自動売買ナビ")

    combined_options = []
    if st.session_state.watchlist:
        for item in st.session_state.watchlist:
            combined_options.append(
                f"⭐ [ウォッチ] {item['Ticker']} - {item['銘柄名']}"
            )

    if not df_raw.empty and "Ticker" in df_raw.columns:
        for _, row in df_raw.iterrows():
            name = row.get("銘柄名", row["Ticker"])
            opt = f"📋 [推奨] {row['Ticker']} - {name}"
            if opt not in combined_options:
                combined_options.append(opt)

    if combined_options:
        selected_option = st.selectbox(
            "分析する銘柄を選択してください",
            combined_options,
            key="select_analysis_ticker",
        )
        selected_ticker = selected_option.split("] ")[1].split(" - ")[0]
    else:
        selected_ticker = st.text_input(
            "銘柄コードを入力 (例: 7203.T)", value="7203.T"
        )

    col_opt1, col_opt2, col_opt3 = st.columns([2, 2, 1])
    with col_opt1:
        timeframe_option = st.selectbox(
            "⏱ 時間足 (ローソク足の間隔)",
            ["日足 (1日)", "5分足", "15分足", "1時間足", "週足 (1週間)"],
            index=0,
        )
    with col_opt2:
        period_option = st.selectbox(
            "📅 表示対象期間",
            [
                "1日 (1d)",
                "5日 (5d)",
                "1ヶ月 (1mo)",
                "3ヶ月 (3mo)",
                "6ヶ月 (6mo)",
                "1年 (1y)",
            ],
            index=3,
        )
    with col_opt3:
        rr_ratio = st.selectbox(
            "目標リスクリワード比", [1.0, 1.5, 2.0, 2.5], index=1
        )

    tf_map = {
        "5分足": "5m",
        "15分足": "15m",
        "1時間足": "60m",
        "日足 (1日)": "1d",
        "週足 (1週間)": "1wk",
    }
    p_map = {
        "1日 (1d)": "1d",
        "5日 (5d)": "5d",
        "1ヶ月 (1mo)": "1mo",
        "3ヶ月 (3mo)": "3mo",
        "6ヶ月 (6mo)": "6mo",
        "1年 (1y)": "1y",
    }

    interval_val = tf_map[timeframe_option]
    period_val = p_map[period_option]

    if interval_val in ["5m", "15m"] and period_val in ["3mo", "6mo", "1y"]:
        period_val = "1mo"
        st.warning(
            "⚠️ 分足データは直近1ヶ月間（1mo）まで自動調整して取得します。"
        )

    if selected_ticker:
        with st.spinner(
            f"{selected_ticker} ({timeframe_option}) のデータを取得中..."
        ):
            try:
                stock = yf.Ticker(selected_ticker)
                hist = stock.history(period=period_val, interval=interval_val)
                info = stock.info

                if not hist.empty:
                    latest_close = float(hist["Close"].iloc[-1])
                    prev_close = (
                        float(hist["Close"].iloc[-2])
                        if len(hist) > 1
                        else latest_close
                    )
                    change = latest_close - prev_close
                    change_pct = (change / prev_close) * 100 if prev_close != 0 else 0.0

                    company_name = info.get(
                        "longName", info.get("shortName", selected_ticker)
                    )

                    recent_df = hist.tail(20)
                    recent_low = float(recent_df["Low"].min())
                    recent_high = float(recent_df["High"].max())

                    sma20 = float(hist["Close"].rolling(window=20).mean().iloc[-1])
                    if np.isnan(sma20):
                        sma20 = latest_close

                    sma50 = (
                        float(hist["Close"].rolling(window=50).mean().iloc[-1])
                        if len(hist) >= 50
                        else sma20
                    )
                    if np.isnan(sma50):
                        sma50 = sma20

                    if latest_close > sma20 > sma50:
                        trend_type = "BULL"
                        trend_status = "上昇トレンド (買い目線🟢)"
                        entry_side_label = "ロング (買い)"
                        stop_loss = recent_low * 0.995
                        risk = max(latest_close - stop_loss, 1.0)
                        take_profit = latest_close + (risk * rr_ratio)
                        sl_delta_text = f"-{(latest_close - stop_loss)/latest_close*100:.1f}%"
                        tp_delta_text = f"+{(take_profit - latest_close)/latest_close*100:.1f}%"
                        sl_label = "損切りライン (SL) [直近安値]"
                    elif latest_close < sma20:
                        trend_type = "BEAR"
                        trend_status = "下降トレンド (売り目線🔴)"
                        entry_side_label = "ショート (戻り売り)"
                        stop_loss = recent_high * 1.005
                        risk = max(stop_loss - latest_close, 1.0)
                        take_profit = latest_close - (risk * rr_ratio)
                        sl_delta_text = f"+{(stop_loss - latest_close)/latest_close*100:.1f}%"
                        tp_delta_text = f"-{(latest_close - take_profit)/latest_close*100:.1f}%"
                        sl_label = "損切りライン (SL) [直近高値]"
                    else:
                        trend_type = "RANGE"
                        trend_status = "レンジ・転換模索中🟡"
                        entry_side_label = "ロング (レンジ仮定)"
                        stop_loss = recent_low * 0.995
                        risk = max(latest_close - stop_loss, 1.0)
                        take_profit = latest_close + (risk * rr_ratio)
                        sl_delta_text = f"-{(latest_close - stop_loss)/latest_close*100:.1f}%"
                        tp_delta_text = f"+{(take_profit - latest_close)/latest_close*100:.1f}%"
                        sl_label = "損切りライン (SL) [直近安値]"

                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("選択中の銘柄", company_name)
                    with c2:
                        st.metric(
                            "最新株価",
                            f"¥{latest_close:,.1f}",
                            f"{change:+.1f} ({change_pct:+.2f}%)",
                        )
                    with c3:
                        st.metric("ダウ理論・トレンド判定", trend_status)

                    st.markdown(
                        "#### ⚡ YTT風・自動売買ラインナビ (トレンド順張り対応)"
                    )
                    ytt1, ytt2, ytt3, ytt4 = st.columns(4)
                    with ytt1:
                        st.metric(
                            "推奨エントリー",
                            f"¥{latest_close:,.1f}",
                            delta=f"戦略: {entry_side_label}",
                            delta_color="off",
                        )
                    with ytt2:
                        st.metric(
                            sl_label,
                            f"¥{stop_loss:,.1f}",
                            delta=sl_delta_text,
                            delta_color="inverse",
                        )
                    with ytt3:
                        st.metric(
                            f"目標利確 (TP) [RR {rr_ratio}]",
                            f"¥{take_profit:,.1f}",
                            delta=tp_delta_text,
                        )
                    with ytt4:
                        st.metric("想定リスクリワード", f"1 : {rr_ratio}")

                    hist["SMA20"] = hist["Close"].rolling(window=20).mean()
                    hist["SMA50"] = hist["Close"].rolling(window=50).mean()

                    fig_stock = go.Figure()
                    fig_stock.add_trace(
                        go.Candlestick(
                            x=hist.index,
                            open=hist["Open"],
                            high=hist["High"],
                            low=hist["Low"],
                            close=hist["Close"],
                            name="株価",
                        )
                    )
                    fig_stock.add_trace(
                        go.Scatter(
                            x=hist.index,
                            y=hist["SMA20"],
                            mode="lines",
                            name="20本移動平均",
                            line=dict(color="orange", width=1.5),
                        )
                    )
                    fig_stock.add_trace(
                        go.Scatter(
                            x=hist.index,
                            y=hist["SMA50"],
                            mode="lines",
                            name="50本移動平均",
                            line=dict(color="blue", width=1.5),
                        )
                    )

                    tp_color = "green" if trend_type == "BULL" else "red"
                    sl_color = "red" if trend_type == "BULL" else "green"

                    fig_stock.add_hline(
                        y=take_profit,
                        line_dash="dash",
                        line_color=tp_color,
                        annotation_text=f"利確目標 (TP): ¥{take_profit:,.1f}",
                    )
                    fig_stock.add_hline(
                        y=latest_close,
                        line_dash="dot",
                        line_color="blue",
                        annotation_text=f"現在地/エントリー: ¥{latest_close:,.1f}",
                    )
                    fig_stock.add_hline(
                        y=stop_loss,
                        line_dash="dash",
                        line_color=sl_color,
                        annotation_text=f"損切り (SL): ¥{stop_loss:,.1f}",
                    )

                    fig_stock.update_layout(
                        title=(
                            f"{selected_ticker} のローソク足チャート"
                            f" ({timeframe_option}) & YTT売買ライン"
                            f" [{entry_side_label}]"
                        ),
                        yaxis_title="株価 (JPY)",
                        xaxis_rangeslider_visible=False,
                        height=540,
                        hovermode="x unified",
                    )
                    st.plotly_chart(fig_stock, use_container_width=True)
                else:
                    st.error(
                        f"{selected_ticker} のデータが見つかりませんでした。"
                    )
            except Exception as e:
                st.error(f"データ取得中にエラーが発生しました: {e}")

# =========================================================
# 画面4: 📊 デモ取引・バックテストシミュレーション
# =========================================================
elif menu_selection == "📊 デモ取引・バックテストシミュレーション":
    st.subheader("📊 取引シミュレーション & バックテスト")

    horizon_mode = st.radio(
        "🎯 投資目線（検証スパン）の選択",
        [
            "⚡ 短期トレード目線 (日次スイング)",
            "🏛️ 中長期投資目線 (月次・トレンド重視)",
        ],
        horizontal=True,
    )

    st.markdown("---")

    col_param1, col_param2, col_param3, col_param4 = st.columns(4)
    with col_param1:
        initial_capital = st.number_input(
            "初期投資金額 (JPY)",
            min_value=100_000,
            max_value=10_000_000,
            value=1_000_000,
            step=100_000,
        )
    with col_param2:
        take_profit_pct = (
            st.slider(
                "目標利確ライン (Take Profit %)",
                min_value=1.0,
                max_value=30.0,
                value=8.0 if "短期" in horizon_mode else 15.0,
                step=0.5,
            )
            / 100.0
        )
    with col_param3:
        stop_loss_pct = (
            st.slider(
                "損切りライン (Stop Loss %)",
                min_value=1.0,
                max_value=15.0,
                value=3.0 if "短期" in horizon_mode else 5.0,
                step=0.5,
            )
            / 100.0
        )
    with col_param4:
        if "短期" in horizon_mode:
            simulation_period = st.slider(
                "検証期間 (営業日)", min_value=10, max_value=120, value=60, step=5
            )
            fetch_period = "6mo"
        else:
            simulation_period = st.slider(
                "検証期間 (ヶ月)", min_value=3, max_value=36, value=12, step=3
            )
            fetch_period = "3y"

    sim_ticker_options = []
    if st.session_state.watchlist:
        for item in st.session_state.watchlist:
            sim_ticker_options.append(
                f"⭐ [ウォッチ] {item['Ticker']} - {item['銘柄名']}"
            )
    if not df_raw.empty and "Ticker" in df_raw.columns:
        for _, row in df_raw.iterrows():
            name = row.get("銘柄名", row["Ticker"])
            opt = f"📋 [推奨] {row['Ticker']} - {name}"
            if opt not in sim_ticker_options:
                sim_ticker_options.append(opt)

    if sim_ticker_options:
        selected_sim_opt = st.selectbox(
            "バックテスト対象銘柄の選択", sim_ticker_options
        )
        sim_ticker = selected_sim_opt.split("] ")[1].split(" - ")[0]
    else:
        sim_ticker = st.text_input("銘柄コードを入力", value="7203.T")

    if st.button("🚀 バックテストを実行する", type="primary"):
        with st.spinner(f"【{sim_ticker}】の過去データを検証中..."):
            try:
                stock_sim = yf.Ticker(sim_ticker)
                hist_sim = stock_sim.history(period=fetch_period)

                if not hist_sim.empty:
                    df_sim = hist_sim.tail(simulation_period).copy()

                    capital = initial_capital
                    position = 0
                    entry_price = 0
                    trade_history = []
                    capital_curve = [capital]

                    for idx, row in df_sim.iterrows():
                        close_price = row["Close"]
                        high_price = row["High"]
                        low_price = row["Low"]

                        # エントリー判定 (ポジションがない場合)
                        if position == 0:
                            position = int(capital // close_price)
                            if position > 0:
                                entry_price = close_price
                                capital -= position * entry_price

                        # ポジション保有中の利確 / 損切り判定
                        elif position > 0:
                            tp_price = entry_price * (1 + take_profit_pct)
                            sl_price = entry_price * (1 - stop_loss_pct)

                            # 利確判定
                            if high_price >= tp_price:
                                capital += position * tp_price
                                profit = position * (tp_price - entry_price)
                                trade_history.append({"日付": idx.strftime('%Y-%m-%d'), "種別": "利確", "価格": tp_price, "損益": profit})
                                position = 0
                            # 損切り判定
                            elif low_price <= sl_price:
                                capital += position * sl_price
                                loss = position * (sl_price - entry_price)
                                trade_history.append({"日付": idx.strftime('%Y-%m-%d'), "種別": "損切り", "価格": sl_price, "損益": loss})
                                position = 0

                        current_val = capital + (position * close_price)
                        capital_curve.append(current_val)

                    # 最終日でのポジション手仕舞い評価
                    final_val = capital + (position * df_sim["Close"].iloc[-1])
                    total_return = ((final_val - initial_capital) / initial_capital) * 100

                    c_res1, c_res2, c_res3 = st.columns(3)
                    with c_res1:
                        st.metric("初期資本金", f"¥{initial_capital:,.0f}")
                    with c_res2:
                        st.metric("最終総資産", f"¥{final_val:,.0f}", f"{total_return:+.2f}%")
                    with c_res3:
                        st.metric("総取引数", f"{len(trade_history)} 回")

                    # 資産推移グラフの作成
                    fig_curve = go.Figure()
                    fig_curve.add_trace(
                        go.Scatter(
                            y=capital_curve,
                            mode="lines+markers",
                            name="総資産額 (JPY)",
                            line=dict(color="#00CC96", width=2),
                        )
                    )
                    fig_curve.update_layout(
                        title=f"{sim_ticker} バックテスト期間中の資産推移",
                        xaxis_title="経過日数/ステップ",
                        yaxis_title="資産価値 (JPY)",
                        height=400,
                    )
                    st.plotly_chart(fig_curve, use_container_width=True)

                    if trade_history:
                        st.markdown("##### 📜 売買履歴")
                        st.dataframe(pd.DataFrame(trade_history), use_container_width=True)
                    else:
                        st.info("指定された条件（TP/SL）に達する売買取引は発生しませんでした。")
                else:
                    st.error("シミュレーション用のデータを取得できませんでした。")
            except Exception as e:
                st.error(f"バックテスト実行中にエラーが発生しました: {e}")
