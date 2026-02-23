import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials
import folium
from streamlit_folium import st_folium
from fpdf import FPDF
import re

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="CRM PROSPECTION", page_icon="🌿", layout="wide")

# =====================================================
# LOGO
# =====================================================
try:
    st.image("logo.png", width=200)
except:
    pass

# =====================================================
# STYLE
# =====================================================
st.markdown("""
<style>
.main {background-color:#f4f9f4;}
h1,h2,h3 {color:#0B6E4F;}
.stButton>button {
    background-color:#0B6E4F;
    color:white;
    border-radius:8px;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# AUTH
# =====================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

users = st.secrets.get("users", {})

if not st.session_state.authenticated:

    st.title("🔐 Connexion")

    u = st.text_input("Utilisateur")
    p = st.text_input("Mot de passe", type="password")

    if st.button("Se connecter"):
        if u in users and users[u] == p:
            st.session_state.authenticated = True
            st.session_state.user = u
            st.rerun()
        else:
            st.error("Identifiants incorrects")

    st.stop()

# =====================================================
# GOOGLE SHEETS
# =====================================================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)

SHEET_ID = "COLLER_ICI_ID_DU_SHEET"
sheet = client.open_by_key(SHEET_ID).sheet1

data = sheet.get_all_values()

if len(data) > 1:
    df = pd.DataFrame(data[1:], columns=data[0])
else:
    df = pd.DataFrame()

# =====================================================
# SIDEBAR
# =====================================================
st.sidebar.title("🌿 CRM AGRICOLE")
st.sidebar.write(f"👤 {st.session_state.user}")

if st.sidebar.button("Déconnexion"):
    st.session_state.authenticated = False
    st.rerun()

# =====================================================
# TABS
# =====================================================
tab1, tab2, tab3 = st.tabs(["📝 Nouvelle", "🔎 Clients", "📊 Dashboard"])

# =====================================================
# TAB 1 - NOUVELLE PROSPECTION
# =====================================================
with tab1:

    st.header("Nouvelle Prospection")

    type_client = st.selectbox("Type", ["Particulier", "Société"])

    col1, col2 = st.columns(2)

    with col1:
        date_p = st.date_input("Date", date.today())
        region = st.text_input("Région")
        tel = st.text_input("Téléphone")

    with col2:
        email = st.text_input("Email")
        adresse = st.text_input("Adresse")

    if type_client == "Particulier":
        nom = st.text_input("Nom")
        prenom = st.text_input("Prénom")
        nom_societe = ice = responsable = ""
    else:
        nom_societe = st.text_input("Société")
        ice = st.text_input("ICE")
        responsable = st.text_input("Responsable")
        nom = prenom = ""

    # GPS AUTO
    lien = st.text_input("Lien Google Maps")
    gps = st.text_input("GPS (lat,lon)")

    if lien and not gps:
        match = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", lien)
        if match:
            gps = f"{match.group(1)},{match.group(2)}"

    if gps and not lien:
        lien = f"https://www.google.com/maps?q={gps}"

    # CULTURES
    st.subheader("Cultures")

    cultures_list = ["Tomate","Poivron","Aubergine","Oignon","Melon","Pastèque"]
    selected = st.multiselect("Sélectionner", cultures_list)

    superficies = {}
    total = 0

    for c in selected:
        val = st.number_input(f"Superficie {c} (ha)", 0.0, step=0.1, key=c)
        superficies[c] = val
        total += val

    st.info(f"Superficie Totale: {round(total,2)} ha")

    if st.button("💾 Enregistrer"):
        row = [
            str(date_p),
            st.session_state.user,
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
            lien,
            total,
            ", ".join(selected),
            str(superficies)
        ]
        sheet.append_row(row)
        st.success("Enregistré")
        st.rerun()

# =====================================================
# TAB 2 - CLIENTS
# =====================================================
with tab2:

    if df.empty:
        st.warning("Aucun client")
    else:

        search = st.text_input("Recherche client")

        if search:
            mask = df.apply(lambda r: search.lower() in str(r).lower(), axis=1)
            df_filtered = df[mask]
        else:
            df_filtered = df

        st.dataframe(df_filtered, use_container_width=True)

        if not df_filtered.empty:

            idx = st.selectbox("Sélectionner", df_filtered.index)
            client_data = df_filtered.loc[idx]

            st.subheader("Fiche Client")
            st.write(client_data)

            # CARTE
            if client_data["GPS"]:
                lat, lon = map(float, client_data["GPS"].split(","))
                m = folium.Map(location=[lat, lon], zoom_start=14)
                folium.Marker([lat, lon]).add_to(m)
                st_folium(m, width=700)

            # MODIFIER
            st.subheader("Modifier")
            new_tel = st.text_input("Téléphone", client_data["Telephone"])
            if st.button("Sauvegarder"):
                row_num = idx + 2
                sheet.update(f"J{row_num}", new_tel)
                st.success("Mis à jour")
                st.rerun()

            # SUPPRIMER
            if st.checkbox("Confirmer suppression"):
                if st.button("Supprimer"):
                    row_num = idx + 2
                    sheet.delete_rows(row_num)
                    st.success("Supprimé")
                    st.rerun()

            # PDF
            if st.button("Exporter PDF"):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=10)
                for col in client_data.index:
                    pdf.multi_cell(0, 6, f"{col}: {client_data[col]}")
                pdf.output("fiche.pdf")
                with open("fiche.pdf","rb") as f:
                    st.download_button("Télécharger PDF", f, "fiche.pdf")

# =====================================================
# TAB 3 - DASHBOARD
# =====================================================
with tab3:

    if df.empty:
        st.warning("Pas de données")
    else:
        df["Superficie Totale"] = pd.to_numeric(df["Superficie Totale"], errors="coerce").fillna(0)

        col1, col2 = st.columns(2)
        col1.metric("Total Clients", len(df))
        col2.metric("Superficie Totale", round(df["Superficie Totale"].sum(),2))

        st.subheader("Clients par Région")
        st.bar_chart(df["Region"].value_counts())

        st.subheader("Performance Commerciale")
        st.bar_chart(df.groupby("Commerciale")["Superficie Totale"].sum())