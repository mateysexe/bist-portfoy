import streamlit as st
import yfinance as yf
import sqlite3
import uuid
import plotly.express as px

# --- Veritabanı ---
def db_baglanti():
    conn = sqlite3.connect("portfoy.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS portfoy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            sembol TEXT,
            lot INTEGER,
            maliyet REAL
        )
    """)
    conn.commit()
    return conn

st.sidebar.title("🔑 Portföy Kodu")

if "session_id" not in st.session_state:
    st.session_state.session_id = ""

kod_girisi = st.sidebar.text_input("Kodunu gir", value=st.session_state.session_id, max_chars=6).strip().upper()

if st.sidebar.button("✅ Kodu Uygula"):
    st.session_state.session_id = kod_girisi
    st.rerun()

if not st.session_state.session_id:
    import random, string
    yeni_kod = "PF" + ''.join(random.choices(string.digits, k=4))
    st.session_state.session_id = yeni_kod
    st.rerun()

session_id = st.session_state.session_id
st.sidebar.info(f"Kodun: **{session_id}**")
st.sidebar.caption("Bu kodu not al — aynı portföye tekrar erişmek için gerekli.")

def hisseleri_getir():
    conn = db_baglanti()
    rows = conn.execute(
        "SELECT id, sembol, lot, maliyet FROM portfoy WHERE session_id=?",
        (session_id,)
    ).fetchall()
    conn.close()
    return rows

def hisse_ekle(sembol, lot, maliyet):
    s = sembol.upper()
    if not s.endswith(".IS"):
        s += ".IS"
    conn = db_baglanti()
    conn.execute(
        "INSERT INTO portfoy (session_id, sembol, lot, maliyet) VALUES (?,?,?,?)",
        (session_id, s, lot, maliyet)
    )
    conn.commit()
    conn.close()

def hisse_sil(hisse_id):
    conn = db_baglanti()
    conn.execute("DELETE FROM portfoy WHERE id=? AND session_id=?", (hisse_id, session_id))
    conn.commit()
    conn.close()

@st.cache_data(ttl=300)
def fiyat_cek(sembol):
    try:
        bilgi = yf.Ticker(sembol).fast_info
        return bilgi.last_price, bilgi.previous_close
    except:
        return None, None

@st.cache_data(ttl=300)
def gecmis_cek(sembol):
    try:
        return yf.Ticker(sembol).history(period="3mo")
    except:
        return None

# --- Arayüz ---
st.set_page_config(page_title="BIST Portföy Takip", page_icon="📈", layout="wide")
st.title("📈 BIST Portföy Takip")

# Hisse ekleme
st.subheader("Hisse Ekle")
col1, col2, col3, col4 = st.columns([2, 1, 2, 1])
with col1:
    yeni_sembol = st.text_input("Sembol", placeholder="Hisse Kodu (örn: THYAO)", label_visibility="collapsed")
with col2:
    yeni_lot = st.number_input("Lot Sayısı", min_value=1, value=None, placeholder="Lot Sayısı", label_visibility="collapsed")
with col3:
    yeni_maliyet = st.number_input("Maliyet Fiyatı (TL)", min_value=0.01, value=None, placeholder="Maliyet Fiyatı", label_visibility="collapsed")
with col4:
    if st.button("➕ Ekle", use_container_width=True):
        if yeni_sembol:
            hisse_ekle(yeni_sembol, yeni_lot, yeni_maliyet)
            st.success(f"{yeni_sembol.upper()} eklendi!")
            st.rerun()

st.divider()

hisseler = hisseleri_getir()

if not hisseler:
    st.info("Henüz hisse eklenmedi. Yukarıdan ekleyebilirsin.")
else:
    if st.button("🔄 Fiyatları Güncelle"):
        st.cache_data.clear()
        st.rerun()

    satirlar = []
    toplam_maliyet = 0
    toplam_deger = 0

    for hisse_id, sembol, lot, maliyet in hisseler:
        fiyat, onceki = fiyat_cek(sembol)
        if fiyat is None:
            continue
        mt = lot * maliyet
        gd = lot * fiyat
        kz = gd - mt
        kz_yuzde = (kz / mt) * 100
        gunluk = ((fiyat - onceki) / onceki) * 100 if onceki else 0
        toplam_maliyet += mt
        toplam_deger += gd
        satirlar.append({
            "id": hisse_id,
            "Hisse": sembol.replace(".IS", ""),
            "Lot": lot,
            "Maliyet (TL)": maliyet,
            "Güncel Fiyat": fiyat,
            "Günlük %": gunluk,
            "Kar/Zarar %": kz_yuzde,
            "Kar/Zarar TL": kz,
            "Güncel Değer (TL)": gd,
        })

    toplam_kz = toplam_deger - toplam_maliyet
    toplam_kz_yuzde = (toplam_kz / toplam_maliyet) * 100 if toplam_maliyet else 0

    # Özet kartlar
    k1, k2, k3 = st.columns(3)
    k1.metric("💰 Toplam Maliyet", f"{toplam_maliyet:,.0f} TL")
    k2.metric("📊 Güncel Değer", f"{toplam_deger:,.0f} TL")
    k3.metric("📈 Kar / Zarar", f"{toplam_kz:+,.0f} TL", f"%{toplam_kz_yuzde:+.2f}")

    st.divider()

    # Tablo - sütun başlıklarıyla
    st.subheader("Pozisyonlar")
    basliklar = st.columns([2, 1, 1.5, 1.5, 1.2, 1.2, 1.8, 2, 1])
    for b, ad in zip(basliklar, ["Hisse", "Lot", "Maliyet (TL)", "Güncel Fiyat", "Günlük %", "Kar/Zarar %", "Kar/Zarar TL", "Güncel Değer", ""]):
        b.markdown(f"**{ad}**")

    for satir in satirlar:
        c1,c2,c3,c4,c5,c6,c7,c8,c9 = st.columns([2,1,1.5,1.5,1.2,1.2,1.8,2,1])
        c1.write(satir["Hisse"])
        c2.write(satir["Lot"])
        c3.write(f"{satir['Maliyet (TL)']:.2f}")
        c4.write(f"{satir['Güncel Fiyat']:.2f}")
        renk5 = "green" if satir["Günlük %"] > 0 else "red"
        c5.markdown(f"<span style='color:{renk5}'>%{satir['Günlük %']:+.2f}</span>", unsafe_allow_html=True)
        renk6 = "green" if satir["Kar/Zarar %"] > 0 else "red"
        c6.markdown(f"<span style='color:{renk6}'>%{satir['Kar/Zarar %']:+.2f}</span>", unsafe_allow_html=True)
        renk7 = "green" if satir["Kar/Zarar TL"] > 0 else "red"
        c7.markdown(f"<span style='color:{renk7}'>{satir['Kar/Zarar TL']:+,.0f} TL</span>", unsafe_allow_html=True)
        c8.write(f"{satir['Güncel Değer (TL)']:,.0f} TL")
        if c9.button("🗑️", key=f"sil_{satir['id']}"):
            hisse_sil(satir["id"])
            st.rerun()

    st.divider()

    # Pasta grafik
    st.subheader("📊 Portföy Dağılımı")
    fig_pasta = px.pie(
        values=[s["Güncel Değer (TL)"] for s in satirlar],
        names=[s["Hisse"] for s in satirlar],
        hole=0.4
    )
    fig_pasta.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig_pasta, use_container_width=True)

    st.divider()

    # Fiyat geçmişi grafiği
    st.subheader("📈 Fiyat Geçmişi")
    secili = st.selectbox("Hisse seç", [s["Hisse"] for s in satirlar])
    if secili:
        df = gecmis_cek(secili + ".IS")
        if df is not None and not df.empty:
            fig_cizgi = px.line(df, x=df.index, y="Close", title=f"{secili} - 3 Aylık Fiyat")
            fig_cizgi.update_layout(xaxis_title="Tarih", yaxis_title="Fiyat (TL)")
            st.plotly_chart(fig_cizgi, use_container_width=True)
        else:
            st.warning("Grafik verisi alınamadı.")
