import streamlit as st
import yfinance as yf
import plotly.express as px
import random
import string
from supabase import create_client

# --- Supabase bağlantısı ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Yardımcı fonksiyonlar ---
def hisseleri_getir(session_id):
    return supabase.table("portfoy").select("*").eq("session_id", session_id).execute().data

def hisse_ekle(session_id, sembol, lot, maliyet):
    s = sembol.upper()
    if not s.endswith(".IS"):
        s += ".IS"
    supabase.table("portfoy").insert({
        "session_id": session_id,
        "sembol": s,
        "lot": lot,
        "maliyet": maliyet
    }).execute()

def hisse_sil(hisse_id):
    supabase.table("portfoy").delete().eq("id", hisse_id).execute()

def session_kaydet(session_id):
    """Yeni session_id'yi Supabase'e kaydet (zaten varsa sessizce geç)"""
    try:
        supabase.table("sessions").insert({"session_id": session_id}).execute()
    except Exception as e:
        hata = str(e).lower()
        if "duplicate" in hata or "unique" in hata:
            pass  # Zaten kayıtlı, sorun değil
        else:
            st.error(f"Portföy kaydedilemedi: {e}")
            st.stop()

def session_var_mi(session_id):
    """Verilen kod Supabase'de kayıtlı mı?"""
    sonuc = supabase.table("sessions").select("session_id").eq("session_id", session_id).execute().data
    return len(sonuc) > 0

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

# --- Session State başlat ---
if "session_id" not in st.session_state:
    st.session_state.session_id = ""
if "kodu_gosterildi" not in st.session_state:
    st.session_state.kodu_gosterildi = False

# --- Arayüz ---
st.set_page_config(page_title="BIST Portföy Takip", page_icon="📈", layout="wide")
st.title("📈 BIST Portföy Takip")

# --- Karşılama ekranı ---
if not st.session_state.kodu_gosterildi:
    with st.container(border=True):
        st.markdown("### 👋 Hoş Geldiniz")

        sekme1, sekme2 = st.tabs(["🆕 Yeni Portföy Oluştur", "🔑 Mevcut Portföyüme Gir"])

        with sekme1:
            st.caption("Yeni bir portföy kodu oluşturulacak. Bu kodu saklayın — tekrar giriş için gerekecek.")
            yeni_kod_input = st.text_input("Kendi kodunuzu belirleyin (opsiyonel)", placeholder="Örn: PF1234", max_chars=10, key="yeni_kod")

            if st.button("✅ Yeni Portföy Oluştur"):
                if yeni_kod_input.strip():
                    kod = yeni_kod_input.strip().upper()
                    if session_var_mi(kod):
                        st.error("Bu kod zaten kullanımda. Farklı bir kod deneyin veya mevcut portföyünüze giriş yapın.")
                    else:
                        st.session_state.session_id = kod
                        session_kaydet(kod)
                        st.session_state.kodu_gosterildi = True
                        st.rerun()
                else:
                    kod = "PF" + ''.join(random.choices(string.digits, k=4))
                    # Çakışma ihtimaline karşı benzersiz kod üret
                    while session_var_mi(kod):
                        kod = "PF" + ''.join(random.choices(string.digits, k=4))
                    st.session_state.session_id = kod
                    session_kaydet(kod)
                    st.session_state.kodu_gosterildi = True
                    st.rerun()

        with sekme2:
            st.caption("Daha önce oluşturduğunuz portföy kodunu girin.")
            mevcut_kod = st.text_input("Portföy Kodunuz", placeholder="Örn: PF1234", max_chars=10, key="mevcut_kod")

            if st.button("🔓 Portföyüme Gir"):
                if not mevcut_kod.strip():
                    st.error("Lütfen bir kod girin.")
                elif not session_var_mi(mevcut_kod.strip().upper()):
                    st.error("Bu kod bulunamadı. Kodu kontrol edin ya da yeni portföy oluşturun.")
                else:
                    st.session_state.session_id = mevcut_kod.strip().upper()
                    st.session_state.kodu_gosterildi = True
                    st.rerun()

    st.stop()

session_id = st.session_state.session_id

# --- Sidebar ---
st.sidebar.title("🔑 Portföy Kodu")
st.sidebar.code(session_id)
st.sidebar.caption("Bu kodu saklayın. Tekrar giriş için gerekecek.")

if st.sidebar.button("🚪 Çıkış Yap / Kod Değiştir"):
    st.session_state.session_id = ""
    st.session_state.kodu_gosterildi = False
    st.rerun()

# --- Admin Paneli ---
with st.sidebar.expander("🔧 Admin", expanded=False):
    admin_sifre = st.text_input("Şifre", type="password", key="admin_sifre")
    if st.button("Giriş", key="admin_giris"):
        if admin_sifre == st.secrets.get("ADMIN_PASSWORD", ""):
            st.session_state.admin_giris = True
        else:
            st.session_state.admin_giris = False
            st.error("Yanlış şifre.")

if st.session_state.get("admin_giris"):
    with st.sidebar.expander("📋 Tüm Portföy Kodları", expanded=True):
        try:
            tum_kodlar = supabase.table("sessions").select("session_id, created_at").order("created_at", desc=True).execute().data
            if tum_kodlar:
                for k in tum_kodlar:
                    tarih = k["created_at"][:10] if k.get("created_at") else "-"
                    st.sidebar.code(f"{k['session_id']}  ({tarih})", language=None)
            else:
                st.sidebar.info("Henüz kayıtlı kod yok.")
        except Exception as e:
            st.sidebar.error(f"Veriler alınamadı: {e}")

# --- Hisse ekleme ---
st.subheader("Hisse Ekle")
col1, col2, col3, col4 = st.columns([2, 1, 2, 1])
with col1:
    yeni_sembol = st.text_input("Sembol", placeholder="Hisse Kodu (örn: ASTOR)", label_visibility="collapsed")
with col2:
    yeni_lot = st.number_input("Lot", min_value=1, value=None, placeholder="Lot Sayısı", label_visibility="collapsed")
with col3:
    yeni_maliyet = st.number_input("Maliyet", min_value=0.01, value=None, placeholder="Maliyet Fiyatı", label_visibility="collapsed")
with col4:
    if st.button("➕ Ekle", use_container_width=True):
        if yeni_sembol and yeni_lot is not None and yeni_maliyet is not None:
            hisse_ekle(session_id, yeni_sembol, int(yeni_lot), float(yeni_maliyet))
            st.success(f"{yeni_sembol.upper()} eklendi!")
            st.rerun()

st.divider()

hisseler = hisseleri_getir(session_id)

if not hisseler:
    st.info("Henüz hisse eklenmedi. Yukarıdan ekleyebilirsin.")
else:
    if st.button("🔄 Fiyatları Güncelle"):
        st.cache_data.clear()
        st.rerun()

    satirlar = []
    toplam_maliyet = 0
    toplam_deger = 0

    for h in hisseler:
        fiyat, onceki = fiyat_cek(h["sembol"])
        if fiyat is None:
            continue
        mt = h["lot"] * h["maliyet"]
        gd = h["lot"] * fiyat
        kz = gd - mt
        kz_yuzde = (kz / mt) * 100
        gunluk = ((fiyat - onceki) / onceki) * 100 if onceki else 0
        toplam_maliyet += mt
        toplam_deger += gd
        satirlar.append({
            "id": h["id"],
            "Hisse": h["sembol"].replace(".IS", ""),
            "Lot": h["lot"],
            "Maliyet (TL)": h["maliyet"],
            "Güncel Fiyat": fiyat,
            "Günlük %": gunluk,
            "Kar/Zarar %": kz_yuzde,
            "Kar/Zarar TL": kz,
            "Güncel Değer (TL)": gd,
        })

    toplam_kz = toplam_deger - toplam_maliyet
    toplam_kz_yuzde = (toplam_kz / toplam_maliyet) * 100 if toplam_maliyet else 0

    k1, k2, k3 = st.columns(3)
    k1.metric("💰 Toplam Maliyet", f"{toplam_maliyet:,.0f} TL")
    k2.metric("📊 Güncel Değer", f"{toplam_deger:,.0f} TL")
    k3.metric("📈 Kar / Zarar", f"{toplam_kz:+,.0f} TL", f"%{toplam_kz_yuzde:+.2f}")

    st.divider()
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

    if satirlar:
        st.subheader("📊 Portföy Dağılımı")
        fig_pasta = px.pie(
            values=[s["Güncel Değer (TL)"] for s in satirlar],
            names=[s["Hisse"] for s in satirlar],
            hole=0.4
        )
        fig_pasta.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_pasta, use_container_width=True)
    else:
        st.warning("Fiyat verisi alınamadı, grafik gösterilemiyor.")

    st.divider()

    if not satirlar:
        st.stop()

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