import streamlit as st
import pandas as pd
from tradingview_screener import Query, col

st.set_page_config(page_title="USTEL1030 Tarayıcı", page_icon="📈", layout="wide")

st.title("📈 USTEL1030 Tarayıcı")
st.caption("EMA10↑EMA30 · F/K ≤ 50 · P/B ≤ 25 · Haftalık Değişim < %15")

if st.button("▶ Tara", type="primary"):
    with st.spinner("TradingView taranıyor..."):
        try:
            count, df = (
                Query()
                .select("name", "close", "change_abs_1W", "price_earnings_ttm", "price_book_ratio", "volume", "market_cap_basic")
                .where(
                    col("EMA10").crosses_above(col("EMA30")),
                    col("change_abs_1W") < 15,
                    col("price_earnings_ttm").between(0, 50),
                    col("price_book_ratio").between(0, 25),
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
                })
                st.success(f"✅ {count} hisse bulundu")
                st.dataframe(
                    df[["Sembol","Fiyat","Haftalık %","F/K","P/B"]],
                    use_container_width=True,
                    hide_index=True
                )
        except Exception as e:
            st.error(f"Hata: {e}")
