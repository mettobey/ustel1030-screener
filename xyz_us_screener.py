import streamlit as st
import json
import requests
import base64
from tradingview_screener import Query, col
from datetime import datetime
import pandas as pd

st.set_page_config(page_title=“XYZ Analizi — US Hisseler”, page_icon=“🔬”, layout=“wide”)

st.title(“🔬 XYZ Analizi — US Hisse Teknik Tarayıcı”)
st.caption(“RSI · MACD · EMA5/50/200 · Destek/Direnç · Hacim · TradingView verisi”)

# — Sabit hisse listesi + isteğe bağlı ek —

DEFAULT_TICKERS = [“BRZE”, “PLTR”, “QBTS”, “OKLO”, “CRSP”, “MRVL”, “NVDA”, “MMED”, “LLY”, “OSCR”]

st.sidebar.header(“⚙️ Ayarlar”)
custom_input = st.sidebar.text_area(
“Hisse listesi (virgülle ayır)”,
value=”, “.join(DEFAULT_TICKERS),
height=200
)
tickers = [t.strip().upper() for t in custom_input.split(”,”) if t.strip()]

save_enabled = st.sidebar.checkbox(“GitHub’a kaydet”, value=False)

# — GitHub kayıt fonksiyonu —

def save_to_github(data: dict):
try:
token = st.secrets[“GITHUB_TOKEN”]
repo = st.secrets[“GITHUB_REPO”]
path = “results/xyz_us_results.json”
url = f”https://api.github.com/repos/{repo}/contents/{path}”
headers = {“Authorization”: f”token {token}”}
r = requests.get(url, headers=headers)
sha = r.json().get(“sha”) if r.status_code == 200 else None
encoded = base64.b64encode(
json.dumps(data, ensure_ascii=False, indent=2).encode()
).decode()
payload = {
“message”: f”XYZ Update {datetime.now().strftime(’%Y-%m-%d %H:%M’)}”,
“content”: encoded
}
if sha:
payload[“sha”] = sha
requests.put(url, headers=headers, json=payload)
return True
except Exception as e:
st.sidebar.error(f”GitHub hatası: {e}”)
return False

# — Teknik değerlendirme motoru —

def xyz_degerlendir(row):
fiyat    = row.get(“Fiyat”)
rsi      = row.get(“RSI”)
macd     = row.get(“MACD”)
macd_sig = row.get(“MACD_Signal”)
ema5     = row.get(“EMA5”)
ema50    = row.get(“EMA50”)
ema200   = row.get(“EMA200”)
volume   = row.get(“Hacim”)
vol_avg  = row.get(“Hacim_Ort”)

```
puan = 0
pozitif = []
negatif = []

# RSI
if rsi is not None:
    if rsi < 30:
        rsi_label = f"{rsi:.1f} 🟢 Aşırı Satım"
        rsi_color = "green"
        puan += 2
        pozitif.append("RSI aşırı satım bölgesinde")
    elif rsi < 45:
        rsi_label = f"{rsi:.1f} 🟡 Satım Yakını"
        rsi_color = "orange"
        puan += 1
        pozitif.append("RSI dip bölgesine yakın")
    elif rsi < 60:
        rsi_label = f"{rsi:.1f} ⚪ Nötr"
        rsi_color = "gray"
    elif rsi < 70:
        rsi_label = f"{rsi:.1f} 🟡 Alım Yakını"
        rsi_color = "orange"
        puan -= 1
        negatif.append("RSI alım bölgesine yakın")
    else:
        rsi_label = f"{rsi:.1f} 🔴 Aşırı Alım"
        rsi_color = "red"
        puan -= 2
        negatif.append("RSI aşırı alım — düzeltme riski")
else:
    rsi_label = "— Veri yok"
    rsi_color = "gray"

# MACD
if macd is not None and macd_sig is not None:
    if macd > macd_sig:
        macd_label = f"{macd:.3f} ✅ Pozitif"
        puan += 1
        pozitif.append("MACD sinyal üstünde")
    else:
        macd_label = f"{macd:.3f} ❌ Negatif"
        puan -= 1
        negatif.append("MACD sinyal altında")
else:
    macd_label = "— Veri yok"

# EMA
ema_satirlar = []
if fiyat:
    for label, val in [("EMA5", ema5), ("EMA50", ema50), ("EMA200", ema200)]:
        if val:
            if fiyat > val:
                ema_satirlar.append(f"{label} ✅")
                puan += 1
                pozitif.append(f"Fiyat {label} üstünde")
            else:
                ema_satirlar.append(f"{label} ❌")
                puan -= 1
                negatif.append(f"Fiyat {label} altında")
ema_label = " / ".join(ema_satirlar) if ema_satirlar else "— Veri yok"

# Hacim
if volume and vol_avg and vol_avg > 0:
    oran = volume / vol_avg
    if oran > 1.5:
        hacim_label = f"📈 Ortalamanın {oran:.1f}x üstünde"
        puan += 1
        pozitif.append("Yüksek hacim")
    elif oran > 0.8:
        hacim_label = f"➡️ Normal ({oran:.1f}x)"
    else:
        hacim_label = f"📉 Düşük ({oran:.1f}x)"
        negatif.append("Hacim ortalamanın altında")
else:
    hacim_label = "— Veri yok"

# Genel sinyal
if puan >= 4:
    sinyal = "🟢 GÜÇLÜ AL"
    sinyal_renk = "#1a3829"
elif puan >= 2:
    sinyal = "🟡 AL / İZLE"
    sinyal_renk = "#3d2e00"
elif puan >= 0:
    sinyal = "⚪ NÖTR / BEKLE"
    sinyal_renk = "#21262d"
elif puan >= -2:
    sinyal = "🟠 SATIŞ / DİKKAT"
    sinyal_renk = "#3d1a00"
else:
    sinyal = "🔴 GÜÇLÜ SATIŞ"
    sinyal_renk = "#3d1a1a"

return {
    "RSI": rsi_label,
    "MACD": macd_label,
    "EMA Durumu": ema_label,
    "Hacim": hacim_label,
    "Puan": puan,
    "Sinyal": sinyal,
    "✅ Pozitifler": " · ".join(pozitif) if pozitif else "—",
    "❌ Negatifler": " · ".join(negatif) if negatif else "—",
}
```

# — Ana tarama —

if “xyz_data” not in st.session_state:
st.session_state.xyz_data = None

col1, col2 = st.columns([1, 4])
with col1:
tara_btn = st.button(“▶ XYZ Tara”, type=“primary”, use_container_width=True)
with col2:
st.info(f”Taranacak hisseler: **{’, ’.join(tickers)}**”)

if tara_btn:
with st.spinner(“TradingView’dan veri çekiliyor…”):
try:
count, df = (
Query()
.set_markets(“america”)
.select(
“name”, “close”, “change”, “change|1W”,
“RSI”, “RSI[1]”,
“MACD.macd”, “MACD.signal”,
“EMA5”, “EMA10”, “EMA50”, “EMA200”,
“volume”, “average_volume_10d_calc”,
“High.1M”, “Low.1M”,
)
.where(
col(“name”).isin(tickers)
)
.limit(50)
.get_scanner_data()
)

```
        df = df.rename(columns={
            "name": "Sembol",
            "close": "Fiyat",
            "change": "Günlük %",
            "change|1W": "Haftalık %",
            "RSI": "RSI",
            "RSI[1]": "RSI_Onceki",
            "MACD.macd": "MACD",
            "MACD.signal": "MACD_Signal",
            "EMA5": "EMA5",
            "EMA10": "EMA10",
            "EMA50": "EMA50",
            "EMA200": "EMA200",
            "volume": "Hacim",
            "average_volume_10d_calc": "Hacim_Ort",
            "High.1M": "1M_Yuksek",
            "Low.1M": "1M_Dusuk",
        })

        df = df.reset_index(drop=True)

        # Teknik değerlendirme ekle
        teknik = df.apply(xyz_degerlendir, axis=1, result_type="expand")
        df_xyz = pd.concat([df[["Sembol", "Fiyat", "Günlük %", "Haftalık %"]], teknik], axis=1)
        df_xyz = df_xyz.sort_values("Puan", ascending=False).reset_index(drop=True)

        st.session_state.xyz_data = {
            "df_raw": df,
            "df_xyz": df_xyz,
            "tarih": datetime.now().strftime("%d %B %Y %H:%M"),
        }

    except Exception as e:
        st.error(f"❌ Hata: {e}")
```

# — Sonuçları göster —

if st.session_state.xyz_data:
data = st.session_state.xyz_data
df_xyz = data[“df_xyz”]
df_raw = data[“df_raw”]

```
st.success(f"✅ {len(df_xyz)} hisse çekildi · {data['tarih']} · Kaynak: TradingView")

# Tab yapısı
tab1, tab2, tab3 = st.tabs(["🔬 XYZ Analizi", "📊 Ham Veriler", "📈 Detay"])

with tab1:
    st.subheader("XYZ Teknik Değerlendirme")
    
    # Renkli sinyal tablosu
    def renk_sinyal(val):
        if "GÜÇLÜ AL" in str(val): return "background-color: #1a3829; color: #3fb950"
        if "AL / İZLE" in str(val): return "background-color: #3d2e00; color: #e3b341"
        if "NÖTR" in str(val): return "background-color: #21262d; color: #8b949e"
        if "DİKKAT" in str(val): return "background-color: #3d1a00; color: #ffa657"
        if "GÜÇLÜ SATIŞ" in str(val): return "background-color: #3d1a1a; color: #f85149"
        return ""

    cols_show = ["Sembol", "Fiyat", "Günlük %", "Haftalık %", "RSI", "MACD", "EMA Durumu", "Hacim", "Puan", "Sinyal"]
    styled = (
        df_xyz[cols_show]
        .style
        .applymap(renk_sinyal, subset=["Sinyal"])
        .background_gradient(subset=["Puan"], cmap="RdYlGn", vmin=-5, vmax=5)
        .format({
            "Fiyat": "${:.2f}",
            "Günlük %": "{:.2f}%",
            "Haftalık %": "{:.2f}%",
            "Puan": "{:+.0f}",
        })
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)

    # Detaylı pros/cons
    st.divider()
    st.subheader("📋 Detay — Pozitif / Negatif")
    detail_cols = ["Sembol", "Sinyal", "✅ Pozitifler", "❌ Negatifler"]
    st.dataframe(df_xyz[detail_cols], use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Ham TradingView Verisi")
    raw_cols = ["Sembol", "Fiyat", "Günlük %", "RSI", "RSI_Onceki", "MACD", "MACD_Signal",
                "EMA5", "EMA10", "EMA50", "EMA200", "Hacim", "Hacim_Ort"]
    available = [c for c in raw_cols if c in df_raw.columns]
    st.dataframe(
        df_raw[available].style.format({
            "Fiyat": "${:.2f}",
            "Günlük %": "{:.2f}%",
            "RSI": "{:.1f}",
            "RSI_Onceki": "{:.1f}",
            "MACD": "{:.4f}",
            "MACD_Signal": "{:.4f}",
            "EMA5": "${:.2f}",
            "EMA10": "${:.2f}",
            "EMA50": "${:.2f}",
            "EMA200": "${:.2f}",
        }, na_rep="—"),
        use_container_width=True,
        hide_index=True
    )

with tab3:
    st.subheader("📈 Hisse Detayı")
    secili = st.selectbox("Hisse seç", df_xyz["Sembol"].tolist())
    row_xyz = df_xyz[df_xyz["Sembol"] == secili].iloc[0]
    row_raw = df_raw[df_raw["Sembol"] == secili].iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fiyat", f"${row_raw['Fiyat']:.2f}", f"{row_raw['Günlük %']:.2f}%")
    c2.metric("RSI", f"{row_raw['RSI']:.1f}" if pd.notna(row_raw.get('RSI')) else "—")
    c3.metric("MACD", f"{row_raw['MACD']:.4f}" if pd.notna(row_raw.get('MACD')) else "—")
    c4.metric("Sinyal", row_xyz["Sinyal"])

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**EMA Durumu**")
        for ema in ["EMA5", "EMA10", "EMA50", "EMA200"]:
            val = row_raw.get(ema)
            fiyat = row_raw.get("Fiyat")
            if pd.notna(val) and fiyat:
                emoji = "✅" if fiyat > val else "❌"
                st.write(f"{emoji} {ema}: ${val:.2f} ({'Üstünde' if fiyat > val else 'Altında'})")

    with col_b:
        st.markdown("**Teknik Özet**")
        st.success(row_xyz["✅ Pozitifler"])
        st.error(row_xyz["❌ Negatifler"])

    # 1 aylık aralık
    h1m = row_raw.get("1M_Yuksek")
    l1m = row_raw.get("1M_Dusuk")
    if pd.notna(h1m) and pd.notna(l1m) and h1m and l1m:
        fiyat = row_raw["Fiyat"]
        pct_pos = (fiyat - l1m) / (h1m - l1m) * 100 if h1m != l1m else 50
        st.markdown(f"**1 Aylık Aralık:** ${l1m:.2f} — ${h1m:.2f}")
        st.progress(min(100, max(0, int(pct_pos))), text=f"Fiyat aralıkta %{pct_pos:.0f} pozisyonunda")

# GitHub kayıt
if save_enabled:
    if st.button("📤 GitHub'a Kaydet"):
        payload = {
            "tarih": data["tarih"],
            "hisseler": df_xyz.to_dict(orient="records")
        }
        if save_to_github(payload):
            st.success("✅ GitHub'a kaydedildi!")

st.caption(f"⚠️ Bu analiz yatırım tavsiyesi değildir. Veri kaynağı: TradingView Screener · {data['tarih']}")
```
