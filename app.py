import streamlit as st
import yfinance as yf

# Portföyünü buraya gir: sembol, lot sayısı, ortalama maliyet (TL)
PORTFOY = [
    {"sembol": "ASTOR.IS",  "lot": 50,   "maliyet": 320.00},
    {"sembol": "FROTO.IS",  "lot": 10,   "maliyet": 1850.00},
    {"sembol": "THYAO.IS",  "lot": 100,  "maliyet": 285.00},
    {"sembol": "TUPRS.IS",  "lot": 20,   "maliyet": 480.00},
    {"sembol": "GWIND.IS",  "lot": 200,  "maliyet": 95.00},
    {"sembol": "SISE.IS",   "lot": 150,  "maliyet": 42.00},
    {"sembol": "DOAS.IS",   "lot": 30,   "maliyet": 320.00},
    {"sembol": "KLKIM.IS",  "lot": 50,   "maliyet": 75.00},
    {"sembol": "AEFES.IS",  "lot": 25,   "maliyet": 220.00},
    {"sembol": "VAKFA.IS",  "lot": 500,  "maliyet": 18.00},
    {"sembol": "PAHOL.IS",  "lot": 100,  "maliyet": 55.00},
    {"sembol": "VESBE.IS",  "lot": 80,   "maliyet": 120.00},
]

st.set_page_config(page_title="BIST Portföy", page_icon="📈", layout="wide")
st.title("📈 BIST Portföy Takip")

if st.button("🔄 Fiyatları Güncelle"):
    st.cache_data.clear()

@st.cache_data(ttl=300)
def veri_cek(sembol):
    try:
        bilgi = yf.Ticker(sembol).fast_info
        return bilgi.last_price, bilgi.previous_close
    except:
        return None, None

satirlar = []
toplam_maliyet = 0
toplam_deger = 0

for h in PORTFOY:
    fiyat, onceki = veri_cek(h["sembol"])
    if fiyat is None:
        continue
    
    maliyet_toplam = h["lot"] * h["maliyet"]
    guncel_deger   = h["lot"] * fiyat
    kar_zarar      = guncel_deger - maliyet_toplam
    kar_zarar_yuzde = (kar_zarar / maliyet_toplam) * 100
    gunluk_degisim = ((fiyat - onceki) / onceki) * 100 if onceki else 0

    toplam_maliyet += maliyet_toplam
    toplam_deger   += guncel_deger

    satirlar.append({
        "Hisse":        h["sembol"].replace(".IS", ""),
        "Lot":          h["lot"],
        "Maliyet (TL)": f"{h['maliyet']:.2f}",
        "Güncel Fiyat": f"{fiyat:.2f}",
        "Günlük %":     f"%{gunluk_degisim:+.2f}",
        "Kar/Zarar TL": f"{kar_zarar:+,.0f}",
        "Kar/Zarar %":  f"%{kar_zarar_yuzde:+.2f}",
        "Güncel Değer": f"{guncel_deger:,.0f}",
    })

# Özet kartlar
toplam_kz = toplam_deger - toplam_maliyet
toplam_kz_yuzde = (toplam_kz / toplam_maliyet) * 100 if toplam_maliyet else 0

col1, col2, col3 = st.columns(3)
col1.metric("💰 Toplam Maliyet",  f"{toplam_maliyet:,.0f} TL")
col2.metric("📊 Güncel Değer",    f"{toplam_deger:,.0f} TL")
col3.metric("📈 Toplam Kar/Zarar", f"{toplam_kz:+,.0f} TL", f"%{toplam_kz_yuzde:+.2f}")

st.divider()

# Tablo
st.subheader("Pozisyonlar")
st.dataframe(satirlar, use_container_width=True, hide_index=True)