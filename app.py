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

def get_technical_analysis(symbols):
    if not symbols:
        return ""
    symbol_list = ", ".join(symbols)
    prompt = f"""Analyze these stocks for a Turkish investor: {symbol_list}

For each stock, search for current RSI(14), MACD, EMA10, EMA50, EMA200 values on daily chart.

Then provide a brief analysis table in Turkish with columns:
- Sembol
- RSI (value + overbought/oversold/neutral in Turkish: Aşırı Alım/Aşırı Satım/Nötr)
- MACD (Pozitif/Negatif)
- EMA Durumu (Fiyat EMA10/50/200'ün üzerinde mi altında mı, kısaca)
- Tavsiye (AL ✅ / İZLE 🟡 / SAT/UZAK DUR ❌)
- Kısa yorum (1 cümle Türkçe)

Format as a clean markdown table. Be concise."""

    try:
        messages = [{"role": "user", "content": prompt}]
        tools = [{"type": "web_search_20250305", "name": "web_search"}]
        
        for _ in range(6):
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"Content-Type": "application/json"},
                json={
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 2000,
                    "tools": tools,
                    "messages": messages
                },
                timeout=60
            )
            if not response.ok:
                return f"API Hatası: {response.status_code}"
            
            data = response.json()
            messages.append({"role": "assistant", "content": data["content"]})
            
            tool_uses = [b for b in data["content"] if b["type"] == "tool_use"]
            if data["stop_reason"] == "end_turn" or not tool_uses:
                return "".join(b["text"] for b in data["content"] if b["type"] == "text")
            
            messages.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": b["id"], "content": "Search completed."} 
                for b in tool_uses
            ]})
        
        return "Analiz tamamlanamadı."
    except Exception as e:
        return f"Hata: {str(e)}"

if "df_result" not in st.session_state:
    st.session_state.df_result = None
if "count_result" not in st.session_state:
    st.session_state.count_result = 0
if "analysis" not in st.session_state:
    st.session_state.analysis = None

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
            df = df[~df['Sembol'].str.contains(r'[/\.\-][A-Z]{1,2}$', regex=True)]
            df = df[~df['Sembol'].str.endswith(('W', 'U', 'R', 'WS'))]
            df = df[~df['Sembol'].str.contains(r'^[A-Z]+P[A-Z]?$', regex=True)]
            df = df[~df['Sembol'].str.endswith(('F', 'Y'))]
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
            st.session_state.analysis = None
        except Exception as e:
            st.error(f"Hata: {e}")

if st.session_state.df_result is not None:
    df = st.session_state.df_result
    n = len(df)
    top_n = min(5, n) if n > 0 else 0

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

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📤 GitHub'a Kaydet"):
            save_to_github(df)
            st.success("✅ GitHub'a kaydedildi!")
    with col2:
        if top_n > 0:
            top_symbols = df.head(top_n)['Sembol'].tolist()
            if st.button(f"🔍 Top {top_n} Hisse Teknik Analiz"):
                with st.spinner(f"Top {top_n} hisse için teknik analiz yapılıyor..."):
                    st.session_state.analysis = get_technical_analysis(top_symbols)

    if st.session_state.analysis:
        st.divider()
        st.subheader(f"📊 Top {top_n} Teknik Analiz")
        st.markdown(st.session_state.analysis)
