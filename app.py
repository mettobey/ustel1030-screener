import streamlit as st
from tradingview_screener import Query, col
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="XYZ Analizi - ABD + BIST", page_icon="🔬", layout="wide")

st.title("XYZ Analizi - ABD + BIST Tarayici")
st.caption("RSI - MACD - EMA - Hacim - PEG - Dip Sinyali - TradingView verisi")

DEFAULT_US = ["BRZE", "PLTR", "NVDA", "MRVL", "OKLO", "CEG"]
DEFAULT_BIST = ["AYGAZ", "DOAS", "EREGL"]

st.sidebar.header("Ayarlar")
us_input = st.sidebar.text_area("ABD hisseleri (virgülle)", value=", ".join(DEFAULT_US), height=120)
bist_input = st.sidebar.text_area("BIST hisseleri (virgülle)", value=", ".join(DEFAULT_BIST), height=120)

us_tickers = [t.strip().upper() for t in us_input.split(",") if t.strip()]
bist_tickers = [t.strip().upper() for t in bist_input.split(",") if t.strip()]

def xyz_degerlendir(row):
    fiyat    = row.get("Fiyat")
    rsi      = row.get("RSI")
    rsi_onceki = row.get("RSI_Onceki")
    macd     = row.get("MACD")
    macd_sig = row.get("MACD_Signal")
    ema5     = row.get("EMA5")
    ema50    = row.get("EMA50")
    ema200   = row.get("EMA200")
    volume   = row.get("Hacim")
    vol_avg  = row.get("Hacim_Ort")
    vol_1g   = row.get("Hacim_1G_Once")
    peg      = row.get("PEG")
    bb_alt   = row.get("BB_Alt")
    williams = row.get("Williams")

    puan = 0
    dip_puan = 0
    pozitif = []
    negatif = []
    dip_sinyaller = []

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

    if volume and vol_avg and vol_avg > 0:
        oran = volume / vol_avg
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

        if yon == "artan" and fiyat and ema5 and fiyat > ema5:
            puan += 1
            pozitif.append("Hacim artarken fiyat yukari")
        elif yon == "azalan" and fiyat and ema5 and fiyat < ema5:
            puan += 1
            pozitif.append("Dususte hacim azaliyor (panik yok)")

        if oran > 2.0:
            dip_puan += 1
            dip_sinyaller.append("Hacim spike (kapitulasyon)")
    else:
        hacim_label = "Veri yok"

    if peg is not None and peg > 0:
        if peg < 0.5:
            peg_label = str(round(peg, 2)) + " (cok ucuz)"
            puan += 2
            pozitif.append("PEG cok dusuk")
        elif peg < 1.0:
            peg_label = str(round(peg, 2)) + " (ucuz)"
            puan += 1
            pozitif.append("PEG makul")
        elif peg < 2.0:
            peg_label = str(round(peg, 2)) + " (normal)"
        else:
            peg_label = str(round(peg, 2)) + " (pahali)"
            puan -= 1
            negatif.append("PEG yuksek")
    elif peg is not None and peg <= 0:
        peg_label = str(round(peg, 2)) + " (negatif)"
    else:
        peg_label = "Veri yok"

    if rsi is not None and rsi_onceki is not None:
        if rsi < 40 and rsi > rsi_onceki:
            dip_puan += 2
            dip_sinyaller.append("RSI dipten donuyor (+" + str(round(rsi - rsi_onceki, 1)) + ")")
        elif rsi < 40 and rsi < rsi_onceki:
            dip_sinyaller.append("RSI hala dususte")

    if bb_alt is not None and fiyat:
        if fiyat < bb_alt:
            dip_puan += 1
            dip_sinyaller.append("Bollinger alt bant ALTINDA")
        elif fiyat < bb_alt * 1.02:
            dip_sinyaller.append("Bollinger alt banda yakin")

    if williams is not None:
        if williams < -90:
            dip_puan += 1
            dip_sinyaller.append("Williams %R <-90")
        elif williams < -80:
            dip_sinyaller.append("Williams %R <-80")

    if dip_puan >= 4:
        dip_label = "GUCLU DIP"
    elif dip_puan >= 2:
        dip_label = "KISMI DIP"
    elif dip_puan >= 1:
        dip_label = "ZAYIF ISARET"
    else:
        dip_label = "DIP YOK"

    if puan >= 6:
        sinyal = "GUCLU AL"
    elif puan >= 3:
        sinyal = "AL / IZLE"
    elif puan >= 0:
        sinyal = "NOTR / BEKLE"
    elif puan >= -2:
        sinyal = "DIKKAT / SATIS"
    else:
        sinyal = "GUCLU SATIS"

    return {
        "RSI": rsi_label, "MACD": macd_label, "EMA Durumu": ema_label,
        "Hacim": hacim_label, "PEG": peg_label, "Puan": puan, "Sinyal": sinyal,
        "Dip Puan": dip_puan, "Dip Sinyali": dip_label,
        "Dip Detay": " / ".join(dip_sinyaller) if dip_sinyaller else "-",
        "Pozitifler": " / ".join(pozitif) if pozitif else "-",
        "Negatifler": " / ".join(negatif) if negatif else "-",
    }

def tara_market(market, tickers):
    if not tickers:
        return pd.DataFrame()
    count, df = (
        Query()
        .set_markets(market)
        .select(
            "name", "close", "change", "change|1W",
            "RSI", "RSI[1]", "MACD.macd", "MACD.signal",
            "EMA5", "EMA10", "EMA50", "EMA200",
            "volume", "average_volume_10d_calc", "volume|1",
            "price_earnings_ttm", "price_earnings_growth_ttm",
            "BB.lower", "W.R", "High.1M", "Low.1M",
        )
        .where(col("name").isin(tickers))
        .limit(100)
        .get_scanner_data()
    )
    df = df.rename(columns={
        "name": "Sembol", "close": "Fiyat", "change": "Gunluk %", "change|1W": "Haftalik %",
        "RSI": "RSI", "RSI[1]": "RSI_Onceki", "MACD.macd": "MACD", "MACD.signal": "MACD_Signal",
        "EMA5": "EMA5", "EMA10": "EMA10", "EMA50": "EMA50", "EMA200": "EMA200",
        "volume": "Hacim", "average_volume_10d_calc": "Hacim_Ort", "volume|1": "Hacim_1G_Once",
        "price_earnings_ttm": "Trailing_PE", "price_earnings_growth_ttm": "PEG",
        "BB.lower": "BB_Alt", "W.R": "Williams", "High.1M": "1M_Yuksek", "Low.1M": "1M_Dusuk",
    })
    df = df.reset_index(drop=True)
    df["Market"] = "🇺🇸 ABD" if market == "america" else "🇹🇷 BIST"
    df["PB"] = "$" if market == "america" else "₺"
    return df

if "xyz_data" not in st.session_state:
    st.session_state.xyz_data = None

c1, c2 = st.columns([1, 4])
with c1:
    tara_btn = st.button("Tara", type="primary", use_container_width=True)
with c2:
    st.info(str(len(us_tickers)) + " ABD + " + str(len(bist_tickers)) + " BIST hisse")

if tara_btn:
    with st.spinner("TradingView verisi cekiliyor..."):
        try:
            parts = []
            df_us = tara_market("america", us_tickers)
            if not df_us.empty:
                parts.append(df_us)
            df_bist = tara_market("turkey", bist_tickers)
            if not df_bist.empty:
                parts.append(df_bist)

            if parts:
                df = pd.concat(parts, ignore_index=True)
                teknik = df.apply(xyz_degerlendir, axis=1, result_type="expand")
                df_xyz = pd.concat([df[["Market", "Sembol", "Fiyat", "PB", "Gunluk %", "Haftalik %"]], teknik], axis=1)
                df_xyz = df_xyz.sort_values("Puan", ascending=False).reset_index(drop=True)
                st.session_state.xyz_data = {
                    "df_raw": df, "df_xyz": df_xyz,
                    "tarih": datetime.now().strftime("%d %B %Y %H:%M"),
                }
            else:
                st.warning("Hic veri cekilemedi.")
        except Exception as e:
            st.error("Hata: " + str(e))

if st.session_state.xyz_data:
    data = st.session_state.xyz_data
    df_xyz = data["df_xyz"]
    df_raw = data["df_raw"]

    st.success(str(len(df_xyz)) + " hisse - " + data["tarih"] + " - Kaynak: TradingView")

    def fiyat_goster(row):
        return row["PB"] + "{:.2f}".format(row["Fiyat"])
    df_xyz["Fiyat Gosterim"] = df_xyz.apply(fiyat_goster, axis=1)

    tab1, tab2, tab3, tab4 = st.tabs(["XYZ Analizi", "Dip Avcisi", "Ham Veriler", "Detay"])

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

        cols_show = ["Market", "Sembol", "Fiyat Gosterim", "Gunluk %", "Haftalik %", "RSI", "MACD", "EMA Durumu", "Hacim", "PEG", "Puan", "Sinyal"]
        styled = (
            df_xyz[cols_show]
            .style
            .map(renk_sinyal, subset=["Sinyal"])
            .background_gradient(subset=["Puan"], cmap="RdYlGn", vmin=-5, vmax=8)
            .format({"Gunluk %": "{:.2f}%", "Haftalik %": "{:.2f}%", "Puan": "{:+.0f}"})
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)
        st.divider()
        st.dataframe(df_xyz[["Market", "Sembol", "Sinyal", "Pozitifler", "Negatifler"]], use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("🎯 Dip Avcisi")
        st.caption("RSI donusu + Bollinger alt bant + Williams %R + hacim kapitulasyonu")
        def renk_dip(val):
            if "GUCLU DIP" in str(val):
                return "background-color: #1a3829; color: #3fb950"
            if "KISMI DIP" in str(val):
                return "background-color: #3d2e00; color: #e3b341"
            if "ZAYIF" in str(val):
                return "background-color: #21262d; color: #8b949e"
            return "background-color: #161b22; color: #6e7681"
        df_dip = df_xyz.sort_values("Dip Puan", ascending=False)
        styled_dip = (
            df_dip[["Market", "Sembol", "Fiyat Gosterim", "RSI", "Dip Puan", "Dip Sinyali", "Dip Detay"]]
            .style
            .map(renk_dip, subset=["Dip Sinyali"])
            .background_gradient(subset=["Dip Puan"], cmap="Greens", vmin=0, vmax=5)
            .format({"Dip Puan": "{:.0f}"})
        )
        st.dataframe(styled_dip, use_container_width=True, hide_index=True)

    with tab3:
        raw_cols = ["Market", "Sembol", "Fiyat", "PB", "RSI", "RSI_Onceki", "MACD", "MACD_Signal",
                    "EMA5", "EMA50", "EMA200", "Hacim", "Hacim_Ort", "BB_Alt", "Williams", "Trailing_PE", "PEG"]
        available = [c for c in raw_cols if c in df_raw.columns]
        st.dataframe(df_raw[available], use_container_width=True, hide_index=True)

    with tab4:
        secili = st.selectbox("Hisse sec", df_xyz["Sembol"].tolist())
        row_xyz = df_xyz[df_xyz["Sembol"] == secili].iloc[0]
        row_raw = df_raw[df_raw["Sembol"] == secili].iloc[0]
        pb = row_raw.get("PB", "$")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Fiyat", pb + "{:.2f}".format(row_raw["Fiyat"]), "{:.2f}%".format(row_raw["Gunluk %"]))
        c2.metric("RSI", "{:.1f}".format(row_raw["RSI"]) if pd.notna(row_raw.get("RSI")) else "-")
        c3.metric("Sinyal", row_xyz["Sinyal"])
        c4.metric("Dip Sinyali", row_xyz["Dip Sinyali"])

        c5, c6, c7 = st.columns(3)
        bb = row_raw.get("BB_Alt")
        wr = row_raw.get("Williams")
        peg = row_raw.get("PEG")
        c5.metric("Bollinger Alt", pb + "{:.2f}".format(bb) if pd.notna(bb) else "-")
        c6.metric("Williams %R", "{:.1f}".format(wr) if pd.notna(wr) else "-")
        c7.metric("PEG", "{:.2f}".format(peg) if pd.notna(peg) else "-")

        st.markdown("**Dip Sinyal Detayi:**")
        st.info(row_xyz["Dip Detay"])

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**EMA Durumu**")
            for ema in ["EMA5", "EMA50", "EMA200"]:
                val = row_raw.get(ema)
                fiyat = row_raw.get("Fiyat")
                if pd.notna(val) and fiyat:
                    durum = "Ustunde" if fiyat > val else "Altinda"
                    st.write(ema + ": " + pb + "{:.2f}".format(val) + " - " + durum)
        with col_b:
            st.markdown("**Ozet**")
            st.success(row_xyz["Pozitifler"])
            st.error(row_xyz["Negatifler"])

    st.caption("Yatirim tavsiyesi degildir. Kaynak: TradingView - " + data["tarih"])
