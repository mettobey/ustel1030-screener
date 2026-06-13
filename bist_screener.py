import streamlit as st
from tradingview_screener import Query, col

st.set_page_config(page_title="BIST USTEL1030 Tarayıcı", page_icon="📈", layout="wide")
st.title("📈 BIST USTEL1030 Tarayıcı")
st.caption("EMA10↑EMA30 · F/K ≤ 50 · P/B ≤ 25 · Haftalık Değişim < %15")

if st.button("▶ Tara", type="primary"):
    with st.spinner("Taranıyor..."):
        try:
            count, df = (
                Query()
                .set_markets('turkey')
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
            df['Score'] = 0

            n = len(df)
            if n >= 5:
                top_n = 5
            elif n >= 3:
                top_n = 3
            elif n >= 1:
                top_n = 1
            else:
                top_n = 0

            if top_n > 0:
                hw_idx = df['Haftalık %'].dropna().nsmallest(top_n).index
                df.loc[hw_idx, 'Score'] += 3

                fk_idx = df['F/K'].dropna().nsmallest(top_n).index
                df.loc[fk_idx, 'Score'] += 4

                pb_idx = df['PD/DD'].dropna().nsmallest(top_n).index
                df.loc[pb_idx, 'Score'] += 3

            df = df.sort_values('Score', ascending=False).reset_index(drop=True)

            st.success(f"✅ {count} hisse bulundu")
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

        except Exception as e:
            st.error(f"Hata: {e}")
