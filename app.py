import streamlit as st
from tradingview_screener import Query, col

st.set_page_config(page_title="USTEL1030 Tarayıcı", page_icon="📈", layout="wide")
st.title("📈 USTEL1030 Tarayıcı")

if st.button("▶ Test Et", type="primary"):
    with st.spinner("Sorgulanıyor..."):
        try:
            # Filtresiz, sadece veri geliyor mu diye
            count, df = (
                Query()
                .select('name', 'close', 'change_abs_1W', 'price_earnings_ttm', 'price_book_ratio')
                .limit(10)
                .get_scanner_data()
            )
            st.success(f"✅ Toplam {count} hisse, ilk 10 gösteriliyor")
            st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Hata: {e}")
