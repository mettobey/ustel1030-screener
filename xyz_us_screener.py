import streamlit as st
from tradingview_screener import Query, col
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="XYZ Analizi - US Hisseler", page_icon="🔬", layout="wide")

st.title("XYZ Analizi - US Hisse Teknik Tarayici")
st.caption("RSI - MACD - EMA5/50/200 - Hacim Yonu - Forward PE - TradingView verisi")

DEFAULT_TICKERS = [
    "ONDS", "ABCL", "NKE", "NOW", "BRZE", "QBTS", "OKLO", "CRSP", "MRVL",
    "NVDA", "MMED", "LLY", "CEG", "Q", "LASR", "AVGO", "WWD", "VRT",
    "DRAM", "VST", "ANET", "QXL"
]

st.sidebar.header("Ayarlar")
custom_input = st.sidebar.text_area(
    "Hisse listesi (virgülle ayir)",
    value=", ".join(DEFAULT_TICKERS),
    height=250
)
tickers = [t.strip().upper() for t in custom_input.split(",") if t.strip()]

def xyz_degerlendir(row):
    fiyat    = row.get("Fiyat")
    rsi      = row.get("RSI")
    macd     = row.get("MACD")
    macd_sig = row.get("MACD_Signal")
    ema5     = row.get("EMA5")
    ema50    = row.get("EMA50")
    ema200   = row.get("EMA200")
    volume   = row.get("Hacim")
    vol_avg  = row.get("Hacim_Ort")
    vol_1g   = row.get("Hacim_1G_Once")
    fwd_pe   = row.get("Forward_PE")
    ttm_pe   = row.get("Trailing_PE")

    puan = 0
    pozitif = []
    negatif = []

    # RSI
    if rsi is not None:
        if rsi < 30:
            rsi_label = str(round(rsi, 1)) + " Asiri Satim"
            puan += 2
            pozitif.append("RSI asiri satim")
        elif rsi < 45:
            rsi_label = str(round(rsi, 1)) + " Satim Yakini"
            puan += 1
            pozitif.append("RSI dip yakini")
        elif rsi < 60:
            rsi_label = str(round(rsi, 1)) + " Notr"
        elif rsi < 70:
            rsi_label = str(round(rsi, 1)) + " Alim Yakini"
            puan -= 1
            negatif.append("RSI alim yakini")
        else:
            rsi_label = str(round(rsi, 1)) + " Asiri Alim"
            puan -= 2
            negatif.append("RSI asiri alim")
    else:
        rsi_label = "Veri yok"

    # MACD
    if macd is not None and macd_sig is not None:
        if macd > macd_sig:
            macd_label = str(round(macd, 3)) + " Pozitif"
            puan += 1
            pozitif.append("MACD pozitif")
        else:
            macd_label = str(round(macd, 3)) + " Negatif"
            puan -= 1
            negatif.append("MACD negatif")
    else:
        macd_label = "Veri yok"

    # EMA
    ema_satirlar = []
    if fiyat:
        for label, val in [("EMA5", ema5), ("EMA50", ema50), ("EMA200", ema200)]:
            if val:
                if fiyat > val:
                    ema_satirlar.append(label + " OK")
                    puan += 1
                    pozitif.append("Fiyat " + label + " ustunde")
                else:
                    ema_satirlar.append(label + " ALTI")
                    puan -= 1
                    negatif.append("Fiyat " + label + " altinda")
    ema_label = " / ".join(ema_satirlar) if ema_satirlar else "Veri yok"

    # Hacim seviyesi + yonu
    if volume and vol_avg and vol_avg > 0:
        oran = volume / vol_avg
        # Hacim yonu: bugun vs dun
        if vol_1g and vol_1g > 0:
            if volume > vol_1g * 1.1:
                yon = "artan"
            elif volume < vol_1g * 0.9:
                yon = "azalan"
            else:
                yon = "yatay"
        else:
            yon = "?"

        if oran > 1.5:
            hacim_label = "Yuksek " + str(round(oran, 1)) + "x (" + yon + ")"
            puan += 1
            pozitif.append("Yuksek hacim " + yon)
        elif oran > 0.8:
            hacim_label = "Normal " + str(round(oran, 1)) + "x (" + yon + ")"
        else:
            hacim_label = "Dusuk " + str(round(oran, 1)) + "x (" + yon + ")"
            negatif.append("Dusuk hacim")

        # Hacim yonu ek puan
        if yon == "artan" and fiyat and ema5 and fiyat > ema5:
            puan += 1
            pozitif.append("Hacim artarken fiyat yukari")
        elif yon == "azalan" and fiyat and ema5 and fiyat < ema5:
            puan += 1
            pozitif.append("Dususte hacim azaliyor (panik yok)")
    else:
        hacim_label = "Veri yok"

    # Forward PE < Trailing PE => kar buyumesi bekleniyor
    if fwd_pe is not None and ttm_pe is not None and fwd_pe > 0 and ttm_pe > 0:
        if fwd_pe < ttm_pe:
            iyilesme = round((1 - fwd_pe / ttm_pe) * 100, 1)
            pe_label = "Fwd " + str(round(fwd_pe, 1)) + " < TTM " + str(round(ttm_pe, 1)) + " (kar buyumesi +%" + str(iyilesme) + ")"
            puan += 1
            pozitif.append("Forward PE iyilesiyor")
        else:
            pe_label = "Fwd " + str(round(fwd_pe, 1)) + " > TTM " + str(round(ttm_pe, 1)) + " (kar daralmasi)"
            negatif.append("Forward PE kotulesiyor")
    elif fwd_pe is not None and fwd_pe > 0 and (ttm_pe is None or ttm_pe <= 0):
        pe_label = "Fwd " + str(round(fwd_pe, 1)) + " (TTM negatif/yok)"
    else:
        pe_label = "Veri yok"

    # Genel sinyal
    if puan >= 5:
        sinyal = "GUCLU AL"
    elif puan >= 2:
        sinyal = "AL / IZLE"
    elif puan >= 0:
        sinyal = "NOTR / BEKLE"
    elif puan >= -2:
        sinyal = "DIKKAT / SATIS"
    else:
        sinyal = "GUCLU SATIS"

    return {
        "RSI": rsi_label,
        "MACD": macd_label,
        "EMA Durumu": ema_label,
        "Hacim": hacim_label,
        "Forward PE": pe_label,
        "Puan": puan,
        "Sinyal": sinyal,
        "Pozitifler": " / ".join(pozitif) if pozitif else "-",
        "Negatifler": " / ".join(negatif) if negatif else "-",
    }

if "xyz_data" not in st.session_state:
    st.session_state.xyz_data = None

c1, c2 = st.columns([1, 4])
with c1:
    tara_btn = st.button("Tara", type="primary", use_container_width=True)
with c2:
    st.info(str(len(tickers)) + " hisse taranacak")

if tara_btn:
    with st.spinner("TradingView verisi cekiliyor..."):
        try:
            count, df = (
                Query()
                .set_markets("america")
                .select(
                    "name", "close", "change", "change|1W",
                    "RSI", "RSI[1]",
                    "MACD.macd", "MACD.signal",
                    "EMA5", "EMA10", "EMA50", "EMA200",
                    "volume", "average_volume_10d_calc", "volume|1",
                    "price_earnings_ttm", "price_earnings",
                    "High.1M", "Low.1M",
                )
                .where(col("name").isin(tickers))
                .limit(100)
                .get_scanner_data()
            )

            df = df.rename(columns={
                "name": "Sembol",
                "close": "Fiyat",
                "change": "Gunluk %",
                "change|1W": "Haftalik %",
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
                "volume|1": "Hacim_1G_Once",
                "price_earnings_ttm": "Trailing_PE",
                "price_earnings_fwd": "Forward_PE",
                "High.1M": "1M_Yuksek",
                "Low.1M": "1M_Dusuk",
            })

            df = df.reset_index(drop=True)
            teknik = df.apply(xyz_degerlendir, axis=1, result_type="expand")
            df_xyz = pd.concat([df[["Sembol", "Fiyat", "Gunluk %", "Haftalik %"]], teknik], axis=1)
            df_xyz = df_xyz.sort_values("Puan", ascending=False).reset_index(drop=True)

            st.session_state.xyz_data = {
                "df_raw": df,
                "df_xyz": df_xyz,
                "tarih": datetime.now().strftime("%d %B %Y %H:%M"),
            }

        except Exception as e:
            st.error("Hata: " + str(e))

if st.session_state.xyz_data:
    data = st.session_state.xyz_data
    df_xyz = data["df_xyz"]
    df_raw = data["df_raw"]

    st.success(str(len(df_xyz)) + " hisse - " + data["tarih"] + " - Kaynak: TradingView")

    tab1, tab2, tab3 = st.tabs(["XYZ Analizi", "Ham Veriler", "Detay"])

    with tab1:
        def renk_sinyal(val):
            if "GUCLU AL" in str(val):
                return "background-color: #1a3829; color: #3fb950"
            if "AL / IZLE" in str(val):
                return "background-color: #3d2e00; color: #e3b341"
            if "NOTR" in str(val):
                return "background-color: #21262d; color: #8b949e"
            if "DIKKAT" in str(val):
                return "background-color: #3d1a00; color: #ffa657"
            if "GUCLU SATIS" in str(val):
                return "background-color: #3d1a1a; color: #f85149"
            return ""

        cols_show = ["Sembol", "Fiyat", "Gunluk %", "Haftalik %", "RSI", "MACD", "EMA Durumu", "Hacim", "Forward PE", "Puan", "Sinyal"]
        styled = (
            df_xyz[cols_show]
            .style
            .applymap(renk_sinyal, subset=["Sinyal"])
            .background_gradient(subset=["Puan"], cmap="RdYlGn", vmin=-5, vmax=7)
            .format({
                "Fiyat": "${:.2f}",
                "Gunluk %": "{:.2f}%",
                "Haftalik %": "{:.2f}%",
                "Puan": "{:+.0f}",
            })
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)
        st.divider()
        st.dataframe(df_xyz[["Sembol", "Sinyal", "Pozitifler", "Negatifler"]], use_container_width=True, hide_index=True)

    with tab2:
        raw_cols = ["Sembol", "Fiyat", "Gunluk %", "RSI", "MACD", "MACD_Signal",
                    "EMA5", "EMA10", "EMA50", "EMA200", "Hacim", "Hacim_Ort", "Hacim_1G_Once",
                    "Trailing_PE", "Forward_PE"]
        available = [c for c in raw_cols if c in df_raw.columns]
        st.dataframe(df_raw[available], use_container_width=True, hide_index=True)

    with tab3:
        secili = st.selectbox("Hisse sec", df_xyz["Sembol"].tolist())
        row_xyz = df_xyz[df_xyz["Sembol"] == secili].iloc[0]
        row_raw = df_raw[df_raw["Sembol"] == secili].iloc[0]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Fiyat", "${:.2f}".format(row_raw["Fiyat"]), "{:.2f}%".format(row_raw["Gunluk %"]))
        c2.metric("RSI", "{:.1f}".format(row_raw["RSI"]) if pd.notna(row_raw.get("RSI")) else "-")
        c3.metric("MACD", "{:.4f}".format(row_raw["MACD"]) if pd.notna(row_raw.get("MACD")) else "-")
        c4.metric("Sinyal", row_xyz["Sinyal"])

        c5, c6 = st.columns(2)
        ttm = row_raw.get("Trailing_PE")
        fwd = row_raw.get("Forward_PE")
        c5.metric("Trailing PE", "{:.1f}".format(ttm) if pd.notna(ttm) else "-")
        c6.metric("Forward PE", "{:.1f}".format(fwd) if pd.notna(fwd) else "-",
                  "iyilesme" if (pd.notna(ttm) and pd.notna(fwd) and fwd > 0 and ttm > 0 and fwd < ttm) else None)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**EMA Durumu**")
            for ema in ["EMA5", "EMA10", "EMA50", "EMA200"]:
                val = row_raw.get(ema)
                fiyat = row_raw.get("Fiyat")
                if pd.notna(val) and fiyat:
                    durum = "Ustunde" if fiyat > val else "Altinda"
                    st.write(ema + ": ${:.2f}".format(val) + " - " + durum)
        with col_b:
            st.markdown("**Ozet**")
            st.success(row_xyz["Pozitifler"])
            st.error(row_xyz["Negatifler"])

        h1m = row_raw.get("1M_Yuksek")
        l1m = row_raw.get("1M_Dusuk")
        if pd.notna(h1m) and pd.notna(l1m) and h1m and l1m:
            fiyat = row_raw["Fiyat"]
            pct_pos = (fiyat - l1m) / (h1m - l1m) * 100 if h1m != l1m else 50
            st.markdown("1 Aylik Aralik: ${:.2f} - ${:.2f}".format(l1m, h1m))
            st.progress(min(100, max(0, int(pct_pos))), text="%{:.0f} pozisyon".format(pct_pos))

    st.caption("Yatirim tavsiyesi degildir. Kaynak: TradingView - " + data["tarih"])
