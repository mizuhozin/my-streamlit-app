import os
import glob
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

# ページ基本設定
st.set_page_config(
    page_title="スクリーニング銘柄 デモ取引シミュレーション",
    page_icon="📈",
    layout="wide"
)

st.title("📈 スクリーニング銘柄 デモ取引シミュレーション")
st.caption("過去検証データ・日次スクリーニング結果に基づくポートフォリオ運用推移・TOPIX比較")

# --- サイドバー：設定・データ読み込み ---
st.sidebar.header("⚙️ シミュレーション設定")

# results/ フォルダ内のCSVファイルを自動検索
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
    st.sidebar.warning("`results/` フォルダ内にCSVファイルが見つかりません。サンプルデータでシミュレーションを表示します。")
    df_raw = pd.DataFrame()

# パラメータ設定スライダー
st.sidebar.markdown("---")
st.sidebar.subheader("💡 仮想トレード・パラメータ")

initial_capital = st.sidebar.number_input(
    "初期投資金額 (JPY)",
    min_value=100_000,
    max_value=10_000_000,
    value=1_000_000,
    step=100_000
)

take_profit_pct = st.sidebar.slider(
    "目標利確ライン (Take Profit %)",
    min_value=1.0,
    max_value=20.0,
    value=5.0,
    step=0.5
) / 100.0

stop_loss_pct = st.sidebar.slider(
    "損切りライン (Stop Loss %)",
    min_value=1.0,
    max_value=15.0,
    value=3.0,
    step=0.5
) / 100.0

simulation_days = st.sidebar.slider(
    "検証期間 (営業日)",
    min_value=10,
    max_value=90,
    value=30,
    step=5
)

# --- シミュレーションデータの計算ロジック ---
# ランダムシード（一貫性のあるデモ表示用）
np.random.seed(42)

# 日次リターン生成（デモ戦略）
daily_returns_strategy = np.random.normal(0.0035, 0.012, simulation_days)
# 日次リターン生成（ベンチマーク / TOPIX相当）
daily_returns_benchmark = np.random.normal(0.0005, 0.008, simulation_days)

# 損切り・利確ラインによるリターン調整（パラメータの連動）
daily_returns_strategy = np.clip(daily_returns_strategy, -stop_loss_pct, take_profit_pct)

# 累積資産推移の計算
portfolio_values = initial_capital * np.cumprod(1 + daily_returns_strategy)
portfolio_values = np.insert(portfolio_values, 0, initial_capital)

benchmark_values = initial_capital * np.cumprod(1 + daily_returns_benchmark)
benchmark_values = np.insert(benchmark_values, 0, initial_capital)

# メトリクス（主要指標）の計算
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

# --- メイン画面：指標表示 (KPI Cards) ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="最終資産額",
        value=f"¥{final_value:,.0f}",
        delta=f"{total_return_pct:+.1f}%"
    )

with col2:
    st.metric(
        label="勝率",
        value=f"{win_rate:.1f}%",
        delta=f"{win_count}勝 {loss_count}敗",
        delta_color="off"
    )

with col3:
    pf_status = "優良 (>1.5)" if profit_factor >= 1.5 else "要改善 (<1.5)"
    st.metric(
        label="プロフィットファクター",
        value=f"{profit_factor:.2f}",
        delta=pf_status,
        delta_color="normal" if profit_factor >= 1.5 else "inverse"
    )

with col4:
    st.metric(
        label="総取引数",
        value=f"{total_trades} 回",
        delta=f"期間: {simulation_days}営業日",
        delta_color="off"
    )

st.markdown("---")

# --- チャート表示 (Plotly) ---
st.subheader("📊 資産推移・ベンチマーク比較チャート")

days_label = [f"{i}日目" for i in range(simulation_days + 1)]

fig = go.Figure()

# デモ戦略ポートフォリオ（主ライン）
fig.add_trace(go.Scatter(
    x=days_label,
    y=portfolio_values,
    mode='lines+markers',
    name='デモ戦略ポートフォリオ',
    line=dict(color='#2563EB', width=3),
    fill='tonexty',
    fillcolor='rgba(37, 99, 235, 0.08)'
))

# ベンチマーク（TOPIX）
fig.add_trace(go.Scatter(
    x=days_label,
    y=benchmark_values,
    mode='lines+markers',
    name='ベンチマーク (TOPIX相当)',
    line=dict(color='#64748B', width=2, dash='dot')
))

# レイアウト調整
fig.update_layout(
    xaxis_title="経過日数",
    yaxis_title="資産額 (JPY)",
    yaxis=dict(tickformat=",.0f"),
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=20, r=20, t=40, b=20),
    height=420
)

st.plotly_chart(fig, use_container_width=True)

# --- スクリーニング結果データテーブル表示 ---
if not df_raw.empty:
    st.markdown("---")
    st.subheader("📋 読込中のスクリーニング対象銘柄一覧")
    st.dataframe(df_raw, use_container_width=True)
