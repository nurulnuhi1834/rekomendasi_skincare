import streamlit as st
import pandas as pd
import owlready2
import os

# ==============================================================================
# 0. KONFIGURASI DAN PEMUATAN ONTOLOGI
# ==============================================================================
ONTOLOGY_FILE_NAME = "skincare_recom - Copy.rdf"
# Ganti dengan nama file Anda, PASTIKAN FILE INI SUDAH DI-UPLOAD KE COLAB!

JENIS_KULIT_OPTIONS = ["kering", "berminyak", "sensitif", "normal", "kombinasi"]
MASALAH_KULIT_OPTIONS = ["jerawat", "kulit_kusam", "bekas_jerawat", "beruntusan", "produksi_minyak_berlebih"]
JENIS_PRODUK_OPTIONS = ["serum", "cleanser", "toner", "sunscreen", "moisturizer"]
BRAND_OPTIONS = ["Semua", "emina", "wardah", "ms glow", "scarlett", "glad2glow"]

@st.cache_resource
def load_ontology():
    if not os.path.exists(ONTOLOGY_FILE_NAME):
        return None

    try:
        # Cek apakah file sudah diupload
        if not os.path.exists(ONTOLOGY_FILE_NAME):
            st.error(f"File ontologi '{ONTOLOGY_FILE_NAME}' tidak ditemukan. Pastikan sudah diupload!")
            return None

        onto = owlready2.get_ontology(ONTOLOGY_FILE_NAME).load()
        with st.spinner("Menyiapkan Knowledge Base..."):
            owlready2.sync_reasoner()

        st.success("Knowledge Base siap digunakan.")
        return onto
    except Exception as e:
        st.error(f"Gagal memuat atau memproses ontologi: {e}")
        return None

# ==============================================================================
# 1. FUNGSI INTI: KNOWLEDGE-BASED QUERY (Menggunakan skema yang sudah diverifikasi)
# ==============================================================================

def get_recommendations_from_ontology(onto, skin_type, concern, product_type, brand):
    """Fungsi query (sama seperti sebelumnya, tidak diubah logikanya)."""
    if onto is None:
        return pd.DataFrame()

    # Perlu mendapatkan nama kelas utama dari ontologi yang dimuat
    # Asumsi: Anda sudah memverifikasi nama kelas 'produk'
    try:
        ProdukKelas = onto.produk
    except AttributeError:
        st.error("Kelas 'produk' tidak ditemukan di ontologi.")
        return pd.DataFrame()


    # --- TAHAP PEMETAAN DAN VALIDASI ---
    onto_skin_type = onto.search_one(iri=f"*{skin_type}")
    onto_concern = onto.search_one(iri=f"*{concern}")
    onto_product_type = onto.search_one(iri=f"*{product_type}")

    onto_brand = onto.search_one(iri=f"*{brand}") if brand.lower() != "semua" and brand else None

    if not all([onto_skin_type, onto_concern, onto_product_type]):
         # Tidak perlu print debug, st.warning sudah cukup untuk UI
         return pd.DataFrame()

    # --- KREASI QUERY PARAMETER (LOGIKA AND) ---
    query_params = {
        'is_a': ProdukKelas,
        'suitable_for': onto_skin_type,
        'address_concern': onto_concern,
        'hasproducttype': onto_product_type
    }

    if onto_brand:
        query_params['hasbrand'] = onto_brand

    # --- EKSEKUSI QUERY ---
    recommended_products = onto.search(**query_params)

    # --- FORMAT OUTPUT ---
    results = []
    for product in recommended_products:

        # Ekstraksi Brand dan Deskripsi
        brand_obj = product.hasbrand.first() if hasattr(product, 'hasbrand') else None
        brand_name = brand_obj.name.replace("_", " ") if brand_obj else "N/A"

        description = product.deskripsi.first() if hasattr(product, 'deskripsi') and product.deskripsi else "Deskripsi tidak tersedia."

        results.append({
            "Produk": product.name.replace("_", " "),
            "Brand": brand_name,
            "Detail Rekomendasi": description
        })

    return pd.DataFrame(results)

# ==============================================================================
# 2. APLIKASI STREAMLIT UTAMA
# ==============================================================================

def main():
    st.set_page_config(layout="wide", page_title="Skincare Recommender KBS")
    st.title("Sistem Rekomendasi Skincare Berbasis Ontologi")
    st.markdown("---")

    # Memuat Ontologi
    onto = load_ontology()

    if onto is None:
        return

    st.header("1. Tentukan Kriteria Anda")

    with st.form(key='reco_form'):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            input_skin = st.selectbox("Jenis Kulit", options=JENIS_KULIT_OPTIONS)
        with col2:
            input_concern = st.selectbox("Masalah Kulit Utama", options=MASALAH_KULIT_OPTIONS)
        with col3:
            input_product = st.selectbox("Jenis Produk yang Dicari", options=JENIS_PRODUK_OPTIONS)
        with col4:
            input_brand = st.selectbox("Preferensi Brand", options=BRAND_OPTIONS)

        submitted = st.form_submit_button("🔍 Dapatkan Rekomendasi Sekarang")

    st.header("2. Hasil Rekomendasi")

    if submitted:
        with st.spinner("Mencari rekomendasi di Knowledge Base..."):
            recommendation_df = get_recommendations_from_ontology(
                onto, input_skin, input_concern, input_product, input_brand
            )

        if recommendation_df.empty:
            st.error("❌ Tidak ditemukan produk yang secara logis memenuhi semua kriteria Anda.")
            st.info("💡 Pastikan produk di Protégé memiliki semua relasi yang sesuai.")
        else:
            st.success(f"✅ Ditemukan {len(recommendation_df)} Produk yang Cocok!")
            st.dataframe(recommendation_df, use_container_width=True, height=500)

if __name__ == '__main__':
    main()