import streamlit as st
import json
import requests
import base64
import pandas as pd
from tradingview_screener import Query, col
from datetime import datetime, date
import numpy as np

st.set_page_config(page_title="USTEL1030 Tarayıcı", page_icon="📈", layout="wide")
st.title("📈 USTEL1030 Tarayıcı")
st.caption("EMA10↑EMA30 · F/K ≤ 50 · P/B ≤ 25 · Haftalık Değişim < %15")

GITHUB_PATH = "results/abd_results.json"

# ---------- ABD borsa tatilleri (2026) ----------
US_HOLIDAYS_2026 = {
    date(2026,1,1), date(2026,1,19), date(2026,2,16), date(2026,4,3),
    date(2026,5,25), date(2026,6,19), date(2026,7,3), date(2026,9,7),
    date(2026,11,26), date(2026,12,25),
}

def is_gunu_say(bas, bit):
    """İki tarih arası iş günü sayısı (hafta sonu + ABD tatilleri hariç)."""
    if bit <= bas:
        return 0
    gun = 0
    d = bas
    while d < bit:
        d = date.fromordinal(d.toordinal() + 1)
        if d.weekday() < 5 and d not in US_HOLIDAYS_2026:
            gun += 1
    return gun

# ---------- GitHub kaydet (append) ----------
def save_to_github(df, mod="Klasik"):
    token = st.secrets["GITHUB_TOKEN"]
    repo = st.secrets["GITHUB_REPO"]
    url = f"https://api.github.com/repos/{repo}/contents/{GITHUB_PATH}"
    headers = {"Authorization": f"token {token}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        sha = r.json().get("sha")
        try:
            mevcut = json.loads(base64.b64decode(r.json()["content"]).decode())
            if not isinstance(mevcut, list):
                mevcut = []
        except Exception:
            mevcut = []
    else:
        sha = None
        mevcut = []
    yeni_kayit = {
        "tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "mod": mod,
        "hisseler": df.to_dict(orient='records')
    }
    mevcut.append(yeni_kayit)
    encoded = base64.b64encode(json.dumps(mevcut, ensure_ascii=False, indent=2).encode()).decode()
    payload = {"message": f"Append {datetime.now().strftime('%Y-%m-%d %H:%M')} {mod}", "content": encoded}
    if sha:
        payload["sha"] = sha
    requests.put(url, headers=headers, json=payload)

def load_from_github():
    repo = st.secrets["GITHUB_REPO"]
    token = st.secrets.get("GITHUB_TOKEN", None)
    url = f"https://api.github.com/repos/{repo}/contents/{GITHUB_PATH}"
    headers = {"Authorization": f"token {token}"} if token else {}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        try:
            data = json.loads(base64.b64decode(r.json()["content"]).decode())
            return data if isinstance(data, list) else []
        except Exception:
            return []
    return []

# ---------- Tavsiye motoru ----------
def tavsiye_uret(rsi, macd, macd_signal, ema10, ema50, ema200, fiyat):
    puanlar = 0
    yorumlar = []
    if rsi is None:
        rsi_durum = "Veri yok"
    elif rsi < 30:
        rsi_durum = f"{rsi:.0f} — Aşırı Satım"; puanlar += 2; yorumlar.append("RSI aşırı satımda")
    elif rsi > 70:
        rsi_durum = f"{rsi:.0f} — Aşırı Alım"; puanlar -= 2; yorumlar.append("RSI aşırı alımda")
    else:
        rsi_durum = f"{rsi:.0f} — Nötr"
    if macd is None or macd_signal is None:
        macd_durum = "Veri yok"
    elif macd > macd_signal:
        macd_durum = "Pozitif ✅"; puanlar += 1; yorumlar.append("MACD pozitif")
    else:
        macd_durum = "Negatif ❌"; puanlar -= 1; yorumlar.append("MACD negatif")
    ema_satirlar = []
    if ema10 and fiyat:
        ema_satirlar.append("EMA10 ✅" if fiyat > ema10 else "EMA10 ❌")
        if fiyat > ema10: puanlar += 1
    if ema50 and fiyat:
        ema_satirlar.append("EMA50 ✅" if fiyat > ema50 else "EMA50 ❌")
        if fiyat > ema50: puanlar += 1
    if ema200 and fiyat:
        ema_satirlar.append("EMA200 ✅" if fiyat > ema200 else "EMA200 ❌")
        if fiyat > ema200: puanlar += 1
    ema_durum = " / ".join(ema_satirlar) if ema_satirlar else "Veri yok"
    if puanlar >= 3:
        tavsiye = "AL ✅"
    elif puanlar >= 1:
        tavsiye = "İZLE 🟡"
    else:
        tavsiye = "UZAK DUR ❌"
    yorum = ", ".join(yorumlar) if yorumlar else "Nötr görünüm"
    return rsi_durum, macd_durum, ema_durum, tavsiye, yorum

def skorla(df):
    df = df.copy().reset_index(drop=True)
    df['Score'] = 0
    n = len(df)
    top_n = 5 if n >= 5 else (3 if n >= 3 else (2 if n >= 2 else (1 if n >= 1 else 0)))
    if top_n > 0:
        df.loc[df['Haftalık %'].dropna().nsmallest(top_n).index, 'Score'] += 3
        df.loc[df['F/K'].dropna().nsmallest(top_n).index, 'Score'] += 4
        df.loc[df['PD/DD'].dropna().nsmallest(top_n).index, 'Score'] += 3
    df = df.sort_values('Score', ascending=False).reset_index(drop=True)
    return df

def teknik_tablo(df, top_n):
    rows = []
    for _, row in df.head(top_n).iterrows():
        rsi_d, macd_d, ema_d, tav, yorum = tavsiye_uret(
            row.get('RSI'), row.get('MACD'), row.get('MACD_Signal'),
            row.get('EMA10'), row.get('EMA50'), row.get('EMA200'), row.get('Fiyat')
        )
        rows.append({'Sembol': row['Sembol'], 'RSI': rsi_d, 'MACD': macd_d,
                     'EMA Durumu': ema_d, 'Tavsiye': tav, 'Yorum': yorum})
    return pd.DataFrame(rows)

def goster_tablo(df):
    st.dataframe(
        df[['Sembol', 'Fiyat', 'Haftalık %', 'F/K', 'PD/DD', 'Score']].style
          .background_gradient(subset=['PD/DD'], cmap='RdYlGn_r')
          .background_gradient(subset=['F/K'], cmap='RdYlGn_r')
          .background_gradient(subset=['Score'], cmap='RdYlGn')
          .format({'Fiyat': '${:.2f}', 'Haftalık %': '{:.2f}%',
                   'F/K': '{:.1f}', 'PD/DD': '{:.2f}', 'Score': '{:.0f}'}),
        use_container_width=True, hide_index=True)

def tarama_yap(ema50_donus=False):
    filtreler = [
        col('EMA10').crosses_above(col('EMA30')),
        col('change|1W') < 15,
        col('price_earnings_ttm').between(0, 50),
        col('price_book_ratio').between(0, 25),
    ]
    count, df = (
        Query()
        .select('name', 'close', 'change|1W', 'price_earnings_ttm', 'price_book_ratio',
                'market_cap_basic', 'RSI', 'MACD.macd', 'MACD.signal', 'EMA10', 'EMA20', 'EMA50', 'EMA200')
        .where(*filtreler)
        .limit(500)
        .get_scanner_data()
    )
    df = df.rename(columns={
        'name': 'Sembol', 'close': 'Fiyat', 'change|1W': 'Haftalık %',
        'price_earnings_ttm': 'F/K', 'price_book_ratio': 'PD/DD',
        'market_cap_basic': 'MCap', 'MACD.macd': 'MACD', 'MACD.signal': 'MACD_Signal',
    })
    if 'ticker' not in df.columns:
        df['ticker'] = df['Sembol']
    if ema50_donus:
        df = df[(df['Fiyat'] > df['EMA50']) & (df['Fiyat'] <= df['EMA50'] * 1.05)]
    df = df[~df['Sembol'].str.contains(r'[/\.\-][A-Z]{1,2}$', regex=True)]
    df = df[~df['Sembol'].str.endswith(('W', 'U', 'R', 'WS'))]
    df = df[~df['Sembol'].str.contains(r'^[A-Z]+P[A-Z]?$', regex=True)]
    df = df[~df['Sembol'].str.endswith(('F', 'Y'))]
    df = df.reset_index(drop=True)
    buyuk = skorla(df[df['MCap'] >= 500_000_000].copy())
    kucuk = skorla(df[df['MCap'] < 500_000_000].copy())
    return count, buyuk, kucuk

def guncel_fiyatlar(semboller):
    """Verilen semboller için TradingView'dan güncel fiyat çeker. {sembol: fiyat}"""
    if not semboller:
        return {}
    try:
        _, df = (
            Query()
            .select('name', 'close')
            .limit(20000)
            .get_scanner_data()
        )
        df = df[df['name'].isin(semboller)]
        return dict(zip(df['name'], df['close']))
    except Exception as e:
        st.error(f"Güncel fiyat çekilemedi: {e}")
        return {}

# ---------- Session ----------
if "buyuk_df" not in st.session_state:
    st.session_state.buyuk_df = None
    st.session_state.kucuk_df = None
    st.session_state.count_result = 0
    st.session_state.mod = ""
    st.session_state.kayit_mesaji = ""

sekme1, sekme2 = st.tabs(["🔍 Tarama", "📈 Performans"])

# ==================== SEKME 1: TARAMA ====================
with sekme1:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("▶ Tara (Klasik)", type="primary", use_container_width=True):
            with st.spinner("Taranıyor ve kaydediliyor..."):
                try:
                    count, buyuk, kucuk = tarama_yap(ema50_donus=False)
                    st.session_state.buyuk_df = buyuk
                    st.session_state.kucuk_df = kucuk
                    st.session_state.count_result = count
                    st.session_state.mod = "Klasik (EMA10↑EMA30)"
                    birlesik = pd.concat([buyuk, kucuk], ignore_index=True)
                    save_to_github(birlesik, "Klasik")
                    st.session_state.kayit_mesaji = "✅ Tarandı ve GitHub'a kaydedildi"
                except Exception as e:
                    st.error(f"Hata: {e}")
    with c2:
        if st.button("▶ Tara (+ EMA50 Dönüş)", use_container_width=True):
            with st.spinner("Taranıyor ve kaydediliyor..."):
                try:
                    count, buyuk, kucuk = tarama_yap(ema50_donus=True)
                    st.session_state.buyuk_df = buyuk
                    st.session_state.kucuk_df = kucuk
                    st.session_state.count_result = len(buyuk) + len(kucuk)
                    st.session_state.mod = "Klasik + EMA50 Dönüş (%0-5)"
                    birlesik = pd.concat([buyuk, kucuk], ignore_index=True)
                    save_to_github(birlesik, "EMA50 Dönüş")
                    st.session_state.kayit_mesaji = "✅ Tarandı ve GitHub'a kaydedildi"
                except Exception as e:
                    st.error(f"Hata: {e}")

    if st.session_state.buyuk_df is not None:
        if st.session_state.get("kayit_mesaji"):
            st.success(st.session_state.kayit_mesaji)
        st.info(f"{st.session_state.mod} — Toplam {st.session_state.count_result} hisse")
        buyuk = st.session_state.buyuk_df
        kucuk = st.session_state.kucuk_df

        st.divider()
        st.header(f"🏢 500M$ Üzeri Şirketler ({len(buyuk)})")
        if len(buyuk) > 0:
            goster_tablo(buyuk)
            bn = min(5, len(buyuk))
            st.subheader(f"📊 500M$ Üzeri — Top {bn} Teknik Analiz")
            st.dataframe(teknik_tablo(buyuk, bn), use_container_width=True, hide_index=True)
        else:
            st.info("Bu kategoride hisse bulunamadı.")

        st.divider()
        st.header(f"🔬 500M$ Altı Micro Şirketler ({len(kucuk)})")
        if len(kucuk) > 0:
            goster_tablo(kucuk)
            kn = min(5, len(kucuk))
            st.subheader(f"📊 500M$ Altı — Top {kn} Teknik Analiz")
            st.dataframe(teknik_tablo(kucuk, kn), use_container_width=True, hide_index=True)
        else:
            st.info("Bu kategoride hisse bulunamadı.")

# ==================== SEKME 2: PERFORMANS ====================
with sekme2:
    st.header("📈 Tavsiye Performansı")
    st.caption("Her taramanın büyük & küçük cap Top 5 tavsiyeleri, giriş fiyatına göre güncel prim.")
    if st.button("▶ Performansı Hesapla", type="primary"):
        with st.spinner("Geçmiş okunuyor ve güncel fiyatlar çekiliyor..."):
            try:
                kayitlar = load_from_github()
                if not kayitlar:
                    st.warning("Kayıt bulunamadı.")
                else:
                    bugun = date.today()
                    # Tüm top5 hisselerini topla
                    satirlar = []
                    tum_semboller = set()
                    for rec in kayitlar:
                        try:
                            kayit_gun = datetime.strptime(rec['tarih'][:10], "%Y-%m-%d").date()
                        except Exception:
                            continue
                        gun_sayisi = is_gunu_say(kayit_gun, bugun)
                        if gun_sayisi < 1:
                            continue  # bugün girenler / iş günü geçmemiş
                        hisseler = rec.get('hisseler', [])
                        big = sorted([h for h in hisseler if h.get('MCap',0) >= 500_000_000],
                                     key=lambda x: x.get('Score',0), reverse=True)[:5]
                        small = sorted([h for h in hisseler if h.get('MCap',0) < 500_000_000],
                                       key=lambda x: x.get('Score',0), reverse=True)[:5]
                        for grup_adi, grup in [("Büyük", big), ("Küçük", small)]:
                            for h in grup:
                                sembol = h['Sembol']
                                tum_semboller.add(sembol)
                                satirlar.append({
                                    'Tarih': rec['tarih'][:10],
                                    'Mod': rec.get('mod', '-'),
                                    'Grup': grup_adi,
                                    'Sembol': sembol,
                                    'Giriş': h['Fiyat'],
                                    'Score': h.get('Score', 0),
                                    'İş Günü': gun_sayisi,
                                })
                    # Güncel fiyatları çek
                    guncel = guncel_fiyatlar(list(tum_semboller))
                    # Primleri hesapla
                    for s in satirlar:
                        gf = guncel.get(s['Sembol'])
                        if gf is None or s['Giriş'] in (None, 0):
                            s['Güncel'] = None
                            s['Prim %'] = None
                            s['Gün Başı %'] = None
                        else:
                            prim = (gf - s['Giriş']) / s['Giriş'] * 100
                            s['Güncel'] = gf
                            s['Prim %'] = prim
                            s['Gün Başı %'] = prim / s['İş Günü'] if s['İş Günü'] > 0 else None

                    df = pd.DataFrame(satirlar)
                    if df.empty:
                        st.info("Henüz iş günü geçmiş (değerlendirilebilir) tavsiye yok.")
                    else:
                        df = df.sort_values(['Tarih','Grup','Score'], ascending=[True, True, False])

                        # Genel özet
                        gecerli = df.dropna(subset=['Prim %'])
                        st.subheader("🎯 Genel Özet")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Ort. Toplam Prim", f"{gecerli['Prim %'].mean():.2f}%")
                        col2.metric("Ort. Gün Başı Prim", f"{gecerli['Gün Başı %'].mean():.3f}%")
                        col3.metric("Kazanan Oranı", f"{(gecerli['Prim %']>0).mean()*100:.0f}%")

                        # Grup bazlı özet
                        st.subheader("📊 Grup Bazlı Ortalama")
                        grup_ozet = gecerli.groupby('Grup').agg(
                            Adet=('Sembol','count'),
                            Ort_Prim=('Prim %','mean'),
                            Ort_GunBasi=('Gün Başı %','mean'),
                            Kazanan=('Prim %', lambda x: f"{(x>0).mean()*100:.0f}%")
                        ).reset_index()
                        st.dataframe(grup_ozet.style.format({'Ort_Prim':'{:.2f}%','Ort_GunBasi':'{:.3f}%'}),
                                     use_container_width=True, hide_index=True)

                        # Detay tablo
                        st.subheader("📋 Detay")
                        goster = df[['Tarih','Grup','Sembol','Score','Giriş','Güncel','İş Günü','Prim %','Gün Başı %']].copy()
                        st.dataframe(
                            goster.style
                              .background_gradient(subset=['Prim %'], cmap='RdYlGn')
                              .format({'Giriş':'${:.2f}','Güncel':'${:.2f}',
                                       'Prim %':'{:.2f}%','Gün Başı %':'{:.3f}%','Score':'{:.0f}'}),
                            use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"Hata: {e}")
