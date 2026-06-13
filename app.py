import streamlit as st
from tradingview_screener import Query, col

st.set_page_config(page_title="USTEL1030 Tarayıcı", page_icon="📈", layout="wide")
st.title("📈 USTEL1030 Tarayıcı")
st.caption("EMA10↑EMA30 · F/K ≤ 50 · P/B ≤ 25 · Haftalık Değişim < %15")

if st.button("▶ Tara", type="primary"):
    with st.spinner("Taranıyor..."):
        try:
            count, df = (
                Query()
                .select('name', 'close', 'change_abs_1W', 'price_earnings_ttm', 'price_book_ratio')
                .where(
                    col('EMA10').crosses_above(col('EMA30')),
                )
                .limit(200)
                .get_scanner_data()
            )

            st.success(f"✅ {count} hisse bulundu")
            st.dataframe(df, use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Hata: {e}")
