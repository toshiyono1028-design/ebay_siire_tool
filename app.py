import streamlit as st
import pandas as pd

# ページ全体のレイアウト設定
st.set_page_config(layout="wide", page_title="eBay相場レンジ検索ツール")

st.title("📸 eBayコンディション別 相場レンジ検索ツール")

# --- コンディション仕分けルール ---
def get_group_key(cond):
    if pd.isna(cond):
        return ""
    c = str(cond).upper().strip()
    if "ALMOST UNUSED" in c or "UNUSED" in c or "BRAND NEW" in c:
        return "① ALMOST UNUSED"
    if "TOP MINT" in c:
        return "② TOP MINT"
    if c == "MINT":
        return "③ MINT"
    if "NEAR MINT" in c or "N.MINT" in c or "OPTICAL MINT" in c or "OPT MINT" in c:
        return "④ NEAR MINT"
    if "EXCELLENT" in c or "EXC" in c:
        return "⑤ EXCELLENT"
    if c != "":
        return "⑥ OTHER"
    return ""

@st.cache_data
def load_data():
    try:
        # スプレッドシートから書き出したCSVを読み込み
        df = pd.read_csv("ebay_data.csv", encoding="utf-8-sig")
        
        # データのクレンジング（空白除去、文字列変換、欠損値処理）
        for col in ["メーカー", "規格", "mm", "F値", "コンディション"]:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"CSVファイルの読み込みエラー: {e}")
        return None

# 安全に並び替えるための補助関数
def safe_sort(array):
    return sorted(list(array), key=lambda x: str(x))

df = load_data()

if df is not None:
    # --- 1. 連動ドロップダウンの作成 ---
    st.subheader("🔍 検索条件を選択してください")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        manufacturers = safe_sort(df[df["メーカー"] != ""]["メーカー"].unique())
        selected_maker = st.selectbox("1. メーカー", ["選択してください"] + manufacturers)
        
    with col2:
        if selected_maker != "選択してください":
            filtered_by_maker = df[df["メーカー"] == selected_maker]
            specs = safe_sort(filtered_by_maker[filtered_by_maker["規格"] != ""]["規格"].unique())
            selected_spec = st.selectbox("2. 規格", ["選択してください"] + specs)
        else:
            selected_spec = st.selectbox("2. 規格", ["先にメーカーを選んでください"], disabled=True)
            
    with col3:
        if selected_maker != "選択してください" and selected_spec != "選択してください":
            filtered_by_spec = df[(df["メーカー"] == selected_maker) & (df["規格"] == selected_spec)]
            mms = safe_sort(filtered_by_spec[filtered_by_spec["mm"] != ""]["mm"].unique())
            selected_mm = st.selectbox("3. 焦点距離 (mm)", ["選択してください"] + mms)
        else:
            selected_mm = st.selectbox("3. 焦点距離 (mm)", ["先に規格を選んでください"], disabled=True)
            
    with col4:
        if selected_maker != "選択してください" and selected_spec != "選択してください" and selected_mm != "選択してください":
            filtered_by_mm = df[
                (df["メーカー"] == selected_maker) & 
                (df["規格"] == selected_spec) & 
                (df["mm"] == selected_mm)
            ]
            f_values = safe_sort(filtered_by_mm[filtered_by_mm["F値"] != ""]["F値"].unique())
            selected_f = st.selectbox("4. 開放F値", ["選択してください"] + f_values)
        else:
            selected_f = st.selectbox("4. 開放F値", ["先にmmを選んでください"], disabled=True)

    # --- 2. 検索実行と結果表示 ---
    if (selected_maker != "選択してください" and 
        selected_spec != "選択してください" and 
        selected_mm != "選択してください" and 
        selected_f != "選択してください"):
        
        final_df = df[
            (df["メーカー"] == selected_maker) & 
            (df["規格"] == selected_spec) & 
            (df["mm"] == selected_mm) & 
            (df["F値"] == selected_f)
        ].copy()
        
        if not final_df.empty:
            st.markdown("---")
            st.success(f"🎯 該当データが **{len(final_df)}件** 見つかりました。")
            
            price_col = "合計(USD)" if "合計(USD)" in df.columns else final_df.columns[-1]
            target_col = "目標仕入額"
            
            # 【重要】売上金額(USD)の数値変換
            final_df[price_col] = pd.to_numeric(final_df[price_col], errors='coerce')
            
            # 【重要】目標仕入額のカンマや記号を自動消去して強制的に数値化する処理
            if target_col in final_df.columns:
                final_df[target_col] = (
                    final_df[target_col]
                    .astype(str)
                    .str.replace("¥", "", regex=False)
                    .str.replace(",", "", regex=False)
                    .str.replace('"', '', regex=False)
                    .str.strip()
                )
                final_df[target_col] = pd.to_numeric(final_df[target_col], errors='coerce')
            
            # 仕分けルールを適用
            final_df["表示コンディション"] = final_df["コンディション"].apply(get_group_key)
            final_df = final_df[final_df["表示コンディション"] != ""]
            
            # グループ化して計算
            agg_dict = {price_col: ["min", "max", "count"]}
            if target_col in final_df.columns:
                agg_dict[target_col] = ["min", "max"]
                
            summary = final_df.groupby("表示コンディション").agg(agg_dict)
            
            # 列名の整理と並び替え
            if target_col in final_df.columns:
                summary.columns = [
                    "売上最安値 (USD)", "売上最高値 (USD)", "該当件数",
                    "目標仕入 最安 (円)", "目標仕入 最高 (円)"
                ]
                summary = summary[[
                    "目標仕入 最安 (円)", "目標仕入 最高 (円)", 
                    "売上最安値 (USD)", "売上最高値 (USD)", "該当件数"
                ]]
            else:
                summary.columns = ["売上最安値 (USD)", "売上最高値 (USD)", "該当件数"]
            
            # 画面表示用の形に綺麗に整形
            summary_display = summary.copy()
            if "売上最安値 (USD)" in summary_display.columns:
                summary_display["売上最安値 (USD)"] = summary_display["売上最安値 (USD)"].map(lambda x: f"${x:,.2f}" if pd.notna(x) else "-")
                summary_display["売上最高値 (USD)"] = summary_display["売上最高値 (USD)"].map(lambda x: f"${x:,.2f}" if pd.notna(x) else "-")
            if target_col in final_df.columns:
                summary_display["目標仕入 最安 (円)"] = summary_display["目標仕入 最安 (円)"].map(lambda x: f"¥{x:,.0f}" if pd.notna(x) else "-")
                summary_display["目標仕入 最高 (円)"] = summary_display["目標仕入 最高 (円)"].map(lambda x: f"¥{x:,.0f}" if pd.notna(x) else "-")
            
            # ① 上部：コンディション別相場表
            st.subheader("📊 コンディション別相場レンジ（統合版）")
            st.dataframe(summary_display, use_container_width=True)
            
            # ② 下部：深掘り詳細リスト
            st.subheader("📂 該当商品の詳細一覧 (価格の安い順)")
            
            show_cols = [c for c in ["商品名", price_col, "表示コンディション", "コンディション", target_col, "仕入れルート"] if c in final_df.columns]
            if not show_cols:
                show_cols = final_df.columns.tolist()
                
            detail_df = final_df[show_cols].sort_values(by=price_col, ascending=True)
            
            detail_display = detail_df.copy()
            if price_col in detail_display.columns:
                detail_display[price_col] = detail_display[price_col].map(lambda x: f"${x:,.2f}" if pd.notna(x) else "-")
            if target_col in detail_display.columns:
                detail_display[target_col] = detail_display[target_col].map(lambda x: f"¥{x:,.0f}" if pd.notna(x) else "-")
                
            st.dataframe(detail_display, use_container_width=True)
            
        else:
            st.warning("選択された条件に一致するデータがありません。")
    else:
        st.info("上のドロップダウンを順番に選択していくと、ここに自動で相場表が作成されます。")