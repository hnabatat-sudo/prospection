import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components
from streamlit_js_eval import get_geolocation
# =====================================================
# CONFIGURATION
# =====================================================
st.set_page_config(page_title="PROSPECTION", page_icon="🌿", layout="wide")

st.image("logo.png", width=180)
st.title("CRM AGRICOLE - PROSPECTION")

# =====================================================
# GOOGLE SHEETS
# =====================================================
SHEET_ID = "1IQm3ua2N_Zn9_-X6h54giefxDXYD1620GuMBlUqOyKA"

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

credentials = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(credentials)
sheet = client.open_by_key(SHEET_ID).sheet1

data = sheet.get_all_records()
df = pd.DataFrame(data)

if not df.empty:
    df.columns = df.columns.str.strip().str.lower()

tab1, tab2, tab3 = st.tabs(
    ["📝 Nouvelle Prospection", "🔎 Base Clients", "📊 Dashboard"]
)

# =====================================================
# ONGLET 1 - NOUVELLE PROSPECTION
# =====================================================
with tab1:

    commercial = st.text_input("Commercial")
    date_prospection = st.date_input("Date", date.today())
    region = st.text_input("Région")

    type_client = st.selectbox("Type de client", ["Particulier", "Société"])

    if type_client == "Particulier":
        nom = st.text_input("Nom")
        prenom = st.text_input("Prénom")
        nom_societe = ""
        ice = ""
        responsable = ""
    else:
        nom_societe = st.text_input("Nom Société")
        ice = st.text_input("ICE")
        responsable = st.text_input("Responsable")
        nom = ""
        prenom = ""

    tel = st.text_input("Téléphone", key="form_tel")
    email = st.text_input("Email", key="form_email")
    adresse = st.text_input("Adresse")

    # ===================== CULTURES =====================
    st.markdown("### 🌾 Cultures")

    liste_cultures = [
        "Tomate","Poivron","Aubergine","Oignon","Courgette",
        "Laitue","Ciboulette","Herbes aromatiques",
        "Melon","Pasteque","Concombre"
    ]

    cultures_selectionnees = st.multiselect(
        "Sélectionner les cultures",
        liste_cultures
    )

    cultures_data = {}
    superficie_totale = 0

    for culture in cultures_selectionnees:
        superficie = st.number_input(
            f"Superficie {culture} (ha)",
            min_value=0.0,
            key=culture
        )
        cultures_data[culture] = superficie
        superficie_totale += superficie

    st.info(f"Superficie totale : {superficie_totale} ha")

    cultures_string = ", ".join(cultures_selectionnees)
    superficies_string = " | ".join(
        [f"{c}:{s}ha" for c, s in cultures_data.items()]
    )

    # ===================== GPS AUTO =====================
    from streamlit_js_eval import get_geolocation

    st.markdown("### 📍 Localisation automatique")

    location = get_geolocation()

    if location:
        gps_lat = location["coords"]["latitude"]
        gps_lon = location["coords"]["longitude"]

        gps = f"{gps_lat},{gps_lon}"
        lien_maps = f"https://www.google.com/maps?q={gps_lat},{gps_lon}"

        st.success("📍 Position détectée automatiquement")
        st.write("Latitude :", gps_lat)
        st.write("Longitude :", gps_lon)
        st.markdown(f"[🌍 Ouvrir dans Google Maps]({lien_maps})")

    else:
        gps = ""
        lien_maps = ""
        st.warning("Cliquez sur Autoriser la localisation dans votre navigateur")
    # ===================== ENREGISTREMENT =====================
    # ==============================
    # FORMULAIRE ENREGISTREMENT
    # ==============================
    with st.form("form_prospection"):

        submit = st.form_submit_button("💾 Enregistrer le client")

        if submit:

            # Vérification anti-doublon (Email + Téléphone)
            existing = df[
                (df["Téléphone"].astype(str) == str(tel)) |
                (df["Email"].astype(str) == str(email))
                ]

            if not existing.empty:
                st.error("⚠️ Client déjà enregistré !")
            else:
                new_row = [
                    str(date_prospection),
                    commercial,
                    region,
                    type_client,
                    nom,
                    prenom,
                    nom_societe,
                    ice,
                    responsable,
                    tel,
                    email,
                    adresse,
                    gps,
                    lien_maps,
                    superficie_totale,
                    cultures_string,
                    superficies_string
                ]

                sheet.append_row(new_row)
                st.success("✅ Client enregistré avec succès !")
                st.balloons()
                st.rerun()
# =====================================================
# ONGLET 2 - BASE CLIENTS
# =====================================================
# =====================================================
# ONGLET 2 - BASE CLIENTS
# =====================================================
with tab2:

    st.subheader("📂 Base Clients")

    if df.empty:
        st.warning("Aucune donnée disponible")
    else:

        st.markdown("### 🔎 Recherche avancée")

        col1, col2, col3 = st.columns(3)

        recherche_nom = col1.text_input("Nom / Société", key="recherche_nom")
        recherche_tel = col2.text_input("Téléphone", key="recherche_tel")
        recherche_region = col3.text_input("Région", key="recherche_region")

        filtered_df = df.copy()

        if recherche_nom:
            filtered_df = filtered_df[
                filtered_df.apply(
                    lambda row: recherche_nom.lower() in str(row).lower(),
                    axis=1
                )
            ]

        if recherche_tel:
            filtered_df = filtered_df[
                filtered_df["Téléphone"].astype(str)
                .str.contains(recherche_tel)
            ]

        if recherche_region:
            filtered_df = filtered_df[
                filtered_df["Region"].astype(str)
                .str.contains(recherche_region)
            ]

        st.dataframe(filtered_df, use_container_width=True)

        # SUPPRESSION CLIENT
        if not filtered_df.empty:

            index_to_delete = st.selectbox(
                "Sélectionner index à supprimer",
                filtered_df.index
            )

            if st.button("🗑 Supprimer Client"):
                sheet.delete_rows(index_to_delete + 2)
                st.success("Client supprimé avec succès")
                st.rerun()
# =====================================================
# ONGLET 3 - DASHBOARD
# =====================================================
with tab3:

    if df.empty:
        st.warning("Aucune donnée disponible")
    else:

        col1, col2 = st.columns(2)
        col1.metric("Total Clients", len(df))
        col2.metric("Régions", df["region"].nunique() if "region" in df.columns else 0)

        if "commercial" in df.columns:
            st.subheader("Clients par Commercial")
            st.bar_chart(df["commercial"].value_counts())

        if "region" in df.columns:
            st.subheader("Clients par Région")
            st.bar_chart(df["region"].value_counts())

        if "gps" in df.columns:
            gps_df = df[df["gps"] != ""]
            if not gps_df.empty:
                coords = gps_df["gps"].str.split(",", expand=True)
                coords.columns = ["lat", "lon"]
                coords["lat"] = pd.to_numeric(coords["lat"], errors="coerce")
                coords["lon"] = pd.to_numeric(coords["lon"], errors="coerce")
                coords = coords.dropna()
                if not coords.empty:
                    st.subheader("Carte globale des clients")
                    st.map(coords)