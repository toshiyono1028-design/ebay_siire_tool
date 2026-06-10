import streamlit as st
import pandas as pd
import io

# 1. ページの設定（ワイドモード）
st.set_page_config(page_title="eBay相場レンジ検索ツール", layout="wide")

# 2. タイトルの表示
st.title("📸 eBayコンディション別 相場レンジ検索ツール")
st.write("---")

# 3. データの読み込み機能
@st.cache_data
def load_data():
    if "csv_data" in st.secrets:
        csv_data = st.secrets["csv_data"]
        df = pd.read_csv(io.StringIO(csv_data))
    else:
        try:
            df = pd.read_csv("ebay_data.csv", encoding="utf-8-sig")
        except:
            st.error("データが見つかりません。スプレッドシートから同期を実行してください。")
            return None
    
    # データのクリーニング
    for col in ["メーカー", "規格", "mm", "F値", "コンディション"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
    return df

df = load_data()

if df is not None:
    # 4. 検索条件の選択
    st.subheader("🔍 検索条件を選択してください")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        manufacturers = ["選択してください"] + sorted(list(df["メーカー"].unique()))
        selected_manufacturer = st.selectbox("1. メーカー", manufacturers)
        
    with col2:
        if selected_manufacturer != "選択してください":
            filtered_df = df[df["メーカー"] == selected_manufacturer]
            standards = ["選択してください"] + sorted(list(filtered_df["規格"].unique()))
            selected_standard = st.selectbox("2. 規格", standards)
        else:
            selected_standard = st.selectbox("2. 規格", ["先にメーカーを選んで..."], disabled=True)
            
    with col3:
        if selected_manufacturer != "選択してください" and selected_standard != "選択してください":
            filtered_df = df[(df["メーカー"] == selected_manufacturer) & (df["規格"] == selected_standard)]
            mms = ["選択してください"] + sorted(list(filtered_df["mm"].unique()))
            selected_mm = st.selectbox("3. 焦点距離 (mm)", mms)
        else:
            selected_mm = st.selectbox("3. 焦点距離 (mm)", ["先に規格を選んで..."], disabled=True)
            
    with col4:
        if selected_manufacturer != "選択してください" and selected_standard != "選択してください" and selected_mm != "選択してください":
            filtered_df = df[(df["メーカー"] == selected_manufacturer) & (df["規格"] == selected_standard) & (df["mm"] == selected_mm)]
            f_values = ["選択してください"] + sorted(list(filtered_df["F値"].unique()))
            selected_f = st.selectbox("4. 開放F値", f_values)
        else:
            selected_f = st.selectbox("4. 開放F値", ["先にmmを選んで..."], disabled=True)
            
    st.write("---")
    
    # 5. 条件がすべて揃ったら相場表と詳細データを展開
    if (selected_manufacturer != "選択してください" and 
        selected_standard != "選択してください" and 
        selected_mm != "選択してください" and 
        selected_f != "選択してください"):
        
        final_filtered_df = df[
            (df["メーカー"] == selected_manufacturer) & 
            (df["規格"] == selected_standard) & 
            (df["mm"] == selected_mm) & 
            (df["F値"] == selected_f)
        ].copy()
        
        if not final_filtered_df.empty:
            st.subheader("📊 コンディション別 相場価格レンジ")
            
            # 【大久保様指定】コンディション定義ロジック
            def get_group_key(cond):
                if pd.isna(cond):
                    return ""
                c = str(cond).upper().strip()
                if "ALMOST UNUSED" in c or "UNUSED" in c or "BRAND NEW" in c:
                    return "① ALMOST UNUSED"
                if "TOP MINT" in c:
                    return "② TOP