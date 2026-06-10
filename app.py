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
            
            # 【完全適用】大久保様指定のコンディション定義ロジック
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
                
            final_filtered_df["統一コンディション"] = final_filtered_df["コンディション"].apply(get_group_key)
            
            # 列名マッピング（スプレッドシートの「商品金額」ヘッダーに対応）
            price_col = "商品金額" if "商品金額" in final_filtered_df.columns else "価格"
            target_col = "目標仕入額" if "目標仕入額" in final_filtered_df.columns else "目標仕入価格"
            
            # ①〜⑥の順番通りにソートして集計するための定義
            conditions_order = [
                "① ALMOST UNUSED", "② TOP MINT", "③ MINT", 
                "④ NEAR MINT", "⑤ EXCELLENT", "⑥ OTHER"
            ]
            
            summary_data = []
            for cond in conditions_order:
                cond_df = final_filtered_df[final_filtered_df["統一コンディション"] == cond]
                if not cond_df.empty:
                    prices = cond_df[price_col].astype(str).str.replace("$", "").str.replace(",", "").astype(float)
                    targets = cond_df[target_col].astype(str).str.replace("¥", "").str.replace(",", "").astype(float)
                    
                    min_price = prices.min()
                    max_price = prices.max()
                    min_target = targets.min()
                    max_target = targets.max()
                    count = len(prices)
                    
                    summary_data.append({
                        "コンディション": cond,
                        "目標仕入額(最低)": f"¥{int(min_target):,}" if not pd.isna(min_target) else "-",
                        "目標仕入額(最高)": f"¥{int(max_target):,}" if not pd.isna(max_target) else "-",
                        "最安値 (USD)": f"${min_price:,.2f}",
                        "最高値 (USD)": f"${max_price:,.2f}",
                        "データ件数": f"{count} 件"
                    })
                    
            if summary_data:
                summary_df = pd.DataFrame(summary_data)
                st.table(summary_df.set_index("コンディション"))
            else:
                st.info("該当するコンディションの価格データがありません。")
            
            # --------------------------------------------------
            # 【完全復元】下部に詳細データ一覧（スプレッドシートの中身）を表示
            # --------------------------------------------------
            st.write("---")
            st.subheader("📋 該当商品の詳細データ一覧")
            st.write("仕入判断の参考として、該当する生データを全列表示しています。")
            
            display_df = final_filtered_df.copy()
            if "統一コンディション" in display_df.columns:
                display_df = display_df.drop(columns=["統一コンディション"])
                
            display_df.index = range(1, len(display_df) + 1)
            st.dataframe(display_df, use_container_width=True)
            
        else:
            st.warning("選択された条件に一致するデータがありませんでした。")
    else:
        st.info("上のドロップダウンを順番に選択していくと、ここに自動で相場表と詳細データが表示されます。")