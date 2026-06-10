import streamlit as st
import pandas as pd
import io

# 1. ページの設定（スマホで見やすいようにワイドモードに設定）
st.set_page_config(page_title="eBay相場レンジ検索ツール", layout="wide")

# 2. タイトルの表示
st.title("📸 eBayコンディション別 相場レンジ検索ツール")
st.write("---")

# 3. データの読み込み機能（GASから送られてくるSecretsのデータを読み込む）
@st.cache_data
def load_data():
    # SecretsからGASが送信したCSV文字列を取得
    if "csv_data" in st.secrets:
        csv_data = st.secrets["csv_data"]
        df = pd.read_csv(io.StringIO(csv_data))
    else:
        # 万が一Secretsが空の場合のセーフティ（既存のCSVを予備で読み込む）
        try:
            df = pd.read_csv("ebay_data.csv", encoding="utf-8-sig")
        except:
            st.error("データが見つかりません。スプレッドシートから同期を実行してください。")
            return None
    
    # データのクリーニング（空白除去、文字列変換、欠損値処理）
    for col in ["メーカー", "規格", "mm", "F値", "コンディション"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
    return df

df = load_data()

if df is not None:
    # 4. 検索条件の選択（ドロップダウン）
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
    
    # 5. 条件がすべて揃ったら相場表を作成・表示
    if (selected_manufacturer != "選択してください" and 
        selected_standard != "選択してください" and 
        selected_mm != "選択してください" and 
        selected_f != "選択してください"):
        
        # 4つの条件でデータを抽出
        final_filtered_df = df[
            (df["メーカー"] == selected_manufacturer) & 
            (df["規格"] == selected_standard) & 
            (df["mm"] == selected_mm) & 
            (df["F値"] == selected_f)
        ].copy()
        
        if not final_filtered_df.empty:
            st.subheader("📊 コンディション別 相場価格レンジ")
            
            # コンディションの表記を綺麗に統一する内部処理
            def clean_condition(c):
                c = str(c).upper().strip()
                if "FOR PARTS" in c or "AS IS" in c or "JUNK" in c:
                    return "Parts/Junk"
                if "BRAND NEW" in c or "UNUSED" in c:
                    return "New/Unused"
                if "TOP MINT" in c:
                    return "Top Mint"
                if "MINT" in c and "NEAR" not in c:
                    return "Mint"
                if "N.MINT" in c or "NEAR MINT" in c or "OPTICAL MINT" in c or "OPT MINT" in c:
                    return "Near Mint"
                if "EXCELLENT" in c or "EXC" in c:
                    return "Excellent"
                if "VERY GOOD" in c or "VG" in c:
                    return "Very Good"
                return "Other"
                
            final_filtered_df["統一コンディション"] = final_filtered_df["コンディション"].apply(clean_condition)
            
            # 各コンディションの最安値・最高値を計算
            summary_data = []
            conditions_order = ["New/Unused", "Top Mint", "Mint", "Near Mint", "Excellent", "Very Good", "Parts/Junk", "Other"]
            
            # スプレッドシートのヘッダー名「商品金額」に合わせて計算（なければ予備で「価格」）
            price_col = "商品金額" if "商品金額" in final_filtered_df.columns else "価格"
            
            for cond in conditions_order:
                cond_df = final_filtered_df[final_filtered_df["統一コンディション"] == cond]
                if not cond_df.empty:
                    # ドルマークやカンマを除去して数値化
                    prices = cond_df[price_col].astype(str).str.replace("$", "").str.replace(",", "").astype(float)
                    min_price = prices.min()
                    max_price = prices.max()
                    count = len(prices)
                    
                    summary_data.append({
                        "コンディション": cond,
                        "データ件数": f"{count} 件",
                        "最安値 (USD)": f"${min_price:,.2f}",
                        "最高値 (USD)": f"${max_price:,.2f}",
                        "価格レンジ": f"${min_price:,.2f} 〜 ${max_price:,.2f}"
                    })
                    
            if summary_data:
                summary_df = pd.DataFrame(summary_data)
                st.table(summary_df.set_index("コンディション"))
            else:
                st.info("該当するコンディションの価格データがありません。")
        else:
            st.warning("選択された条件に一致するデータがありませんでした。")
    else:
        st.info("上のドロップダウンを順番に選択していくと、ここに自動で相場表が作成されます。")