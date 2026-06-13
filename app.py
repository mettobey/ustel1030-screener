import streamlit as st
import pandas as pd
from tradingview_screener import Scanner, Column

st.set_page_config(page_title="USTEL1030 Tarayıcı", page_icon="📈", layout="wide")

st.title("📈 USTEL1030 Tarayıcı")
st.caption("EMA10↑EMA30 · F/K ≤ 50 · P/B ≤ 25 · Haftalık Değişim < %15")

if st.button("▶ Tara", type="primary", use_container_width=False):
    with st.spinner("TradingView taranıyor..."):
        try:
            count, df = (
                Scanner.us()
                .set_markets("america")
                .where(
                    Column("EMA[10]").crosses_above(Column("EMA[30]")),
                    Column("change_abs_1W") < 15,
                    Column("price_earnings_ttm").between(0, 50),
                    Column("price_book_ratio").between(0, 25),
                )
                .get_scanner_data()
            )

            if count == 0:
                st.warning("Kriterlere uyan hisse bulunamadı.")
            else:
                df = df.rename(columns={
                    "name": "Sembol",
                    "close": "Fiyat",
                    "change_abs_1W": "Haftalık %",
                    "price_earnings_ttm": "F/K",
                    "price_book_ratio": "P/B",
                    "market_cap_basic": "Piyasa Değeri",
                    "volume": "Hacim"
                })
                st.success(f"✅ {count} hisse bulundu")
                st.dataframe(
                    df[["Sembol","Fiyat","Haftalık %","F/K","P/B"]],
                    use_container_width=True,
                    hide_index=True
                )
        except Exception as e:
            st.error(f"Hata: {e}")
