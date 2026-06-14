import streamlit as st
import json
import requests
import base64
from tradingview_screener import Query, col
from datetime import datetime

st.set_page_config(page_title="USTEL1030 Tarayıcı", page_icon="📈", layout="wide")
st.title("📈 USTEL1030 Tarayıcı")
st.caption("EMA10↑EMA30 · F/K ≤ 50 · P/B ≤ 25 · Haftalık Değişim < %15")

def save_to_github(df):
    token = st.secrets["GITHUB_TOKEN"]
    repo = st.secrets["GITHUB_REPO"]
    path = "results/abd_results.json"
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    content = {
        "tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "hisseler": df.to_dict(orient='records')
    }
    headers = {"Authorization": f"token {token}"}
    r = requests.get(url, headers=headers)
    sha = r.json().get("sha") if r.status_code == 200 else None
    encoded = base64.b64encode(json.dumps(content, ensure_ascii=False, indent=2).encode()).decode()
    payload = {"message": f"Update {datetime.now().strftime('%Y-%m-%d %H:%M')}", "content": encoded}
    if sha:
        payload["sha"] = sha
    requests.put(url, headers=headers, json=payload)

if "df_result" not in st.session_state:
    st.session_state.df_result = None
if "count_result" not in st.session_state:
    st.session_state.count_result = 0

if st.button("▶ Tara", type="primary"):
    with st.spinner("Taranıyor..."):
        try:
            count, df = (
                Query()
                .select('name', 'close', 'change|1W', 'price_earnings_ttm', 'price_book_ratio')
                .where(
                    col('EMA10').crosses_above(col('EMA30')),
                    col('change|1W') < 15,
                    col('price_earnings_ttm').between(0, 50),
                    col('price_book_ratio').between(0, 25),
                )
                .limit(200)
                .get_scanner_data()
            )

            df = df.rename(columns={
                'name': 'Sembol',
                'close': 'Fiyat',
                'change|1W': 'Haftalık %',
                'price_earnings_ttm': 'F/K',
                'price_book_ratio': 'PD/DD',
            })

            df = df[['Sembol', 'Fiyat', 'Haftalık %', 'F/K', 'PD/DD']].copy()

            # Preferred stock, warrant, unit gibi hisseleri ayıkla
            df = df[~df['Sembol'].str.contains(r'[/\.\-][A-Z]{1,2}$', regex=True)]
            df = df[~df['Sembol'].str.endswith(('W', 'U', 'R', 'WS'))]
            df = df.reset_index(drop=True)

            df['Score'] = 0
            n = len(df)
            top_n = 5 if n >= 5 else (3 if n >= 3 else (1 if n >= 1 else 0))

            if top_n > 0:
                df.loc[df['Haftalık %'].dropna().nsmallest(top_n).index, 'Score'] += 3
                df.loc[df['F/K'].dropna().nsmallest(top_n).index, 'Score'] += 4
                df.loc[df['PD/DD'].dropna().nsmallest(top_n).index, 'Score'] += 3

            df = df.sort_values('Score', ascending=False).reset_index(drop=True)
            st.session_state.df_result = df
            st.session_state.count_result = count

        except Exception as e:
            st.error(f"Hata: {e}")

if st.session_state.df_result is not None:
    df = st.session_state.df_result
    st.success(f"✅ {st.session_state.count_result} hisse bulundu")
    st.dataframe(
        df.style
          .background_gradient(subset=['PD/DD'], cmap='RdYlGn_r')
          .background_gradient(subset=['F/K'], cmap='RdYlGn_r')
          .background_gradient(subset=['Score'], cmap='RdYlGn')
          .format({
              'Fiyat': '${:.2f}',
              'Haftalık %': '{:.2f}%',
              'F/K': '{:.1f}',
              'PD/DD': '{:.2f}',
              'Score': '{:.0f}'
          }),
        use_container_width=True,
        hide_index=True
    )
    if st.button("📤 GitHub'a Kaydet"):
        save_to_github(df)
        st.success("✅ GitHub'a kaydedildi!")
