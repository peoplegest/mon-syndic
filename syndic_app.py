import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Syndic Pro v4", layout="wide", initial_sidebar_state="expanded")

# --- BASE DE DONNÉES ---
DB_FILE = "data_syndic_pro.json"

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {
        "copros": [], "depenses": [], "ag_pv": [], "docs": [], "messages": [],
        "releves_eau": {}, "releves_elec": {"preteur": "", "montant": 0, "kwh": 0, "prix": 0.25},
        "config": {"tantiemes": 1000, "nom_immeuble": "Ma Copropriété"}
    }

def save_data(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

d = load_data()

# --- GESTION DE LA SESSION (CONNEXION) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.role = None
    st.session_state.user_info = None

def login():
    st.title("🔐 Connexion Syndic")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Espace Copropriétaire")
        code = st.text_input("Code d'accès", type="password")
        if st.button("Se connecter (Extranet)"):
            user = next((c for c in d['copros'] if c["Code"] == code), None)
            if user:
                st.session_state.authenticated = True
                st.session_state.role = "Copro"
                st.session_state.user_info = user
                st.rerun()
            else:
                st.error("Code incorrect")

    with col2:
        st.subheader("Espace Administrateur")
        pwd = st.text_input("Mot de passe Admin", type="password")
        if st.button("Se connecter (Syndic)"):
            if pwd == "admin123":
                st.session_state.authenticated = True
                st.session_state.role = "Admin"
                st.rerun()
            else:
                st.error("Mot de passe incorrect")

if not st.session_state.authenticated:
    login()
    st.stop()

# --- SI CONNECTÉ : LOGOUT DANS LA SIDEBAR ---
if st.sidebar.button("🚪 Déconnexion"):
    st.session_state.authenticated = False
    st.rerun()

# --- INTERFACE ADMINISTRATEUR ---
if st.session_state.role == "Admin":
    st.sidebar.title("🛠️ Admin Dashboard")
    menu = st.sidebar.radio("Menu", ["Tableau de Bord", "Comptabilité & Compteurs", "AG & Convocation", "Gestion Copropriétaires"])

    if menu == "Tableau de Bord":
        st.title(f"📊 Dashboard - {d['config']['nom_immeuble']}")
        
        # Indicateurs Clés
        total_charges = sum(x['Montant'] for x in d['depenses'])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Dépenses Totales", f"{total_charges:.2f} €")
        c2.metric("Nb Copropriétaires", len(d['copros']))
        c3.metric("Millièmes total", d['config']['tantiemes'])
        c4.metric("Élec Communes", f"{d['releves_elec']['montant']:.2f} €")

        # Graphique des dépenses
        if d['depenses']:
            df = pd.DataFrame(d['depenses'])
            st.subheader("Analyse des dépenses")
            st.bar_chart(df.set_index('Libellé')['Montant'])

    elif menu == "Comptabilité & Compteurs":
        st.title("🧾 Finances et Relevés")
        tab1, tab2 = st.tabs(["Factures", "Compteurs (Eau/Élec)"])
        
        with tab1:
            with st.form("f"):
                lib = st.text_input("Libellé")
                mt = st.number_input("Montant TTC", min_value=0.0)
                if st.form_submit_button("Ajouter Facture"):
                    d['depenses'].append({"Date": str(datetime.now().date()), "Libellé": lib, "Montant": mt})
                    save_data(d); st.rerun()
            st.table(d['depenses'])

        with tab2:
            st.subheader("💧 Relevés Eau")
            for cp in d['copros']:
                d['releves_eau'][cp['Nom']] = st.number_input(f"m3 {cp['Nom']}", value=d['releves_eau'].get(cp['Nom'], 0))
            
            st.subheader("⚡ Élec Commune")
            preteur = st.selectbox("Qui paye l'élec ?", [c['Nom'] for c in d['copros']])
            kwh = st.number_input("kWh relevés", value=d['releves_elec']['kwh'])
            if st.button("Sauvegarder les relevés"):
                d['releves_elec'] = {"preteur": preteur, "montant": kwh * 0.25, "kwh": kwh, "prix": 0.25}
                save_data(d); st.success("Enregistré")

    elif menu == "AG & Convocation":
        st.title("⚖️ Gestion des Assemblées Générales")
        mode_ag = st.selectbox("Action", ["Rédiger une Convocation", "Saisie du PV d'AG"])
        
        if mode_ag == "Rédiger une Convocation":
            dt = st.date_input("Date de l'AG")
            oj = st.text_area("Ordre du jour")
            if st.button("Générer PDF (Simulé)"):
                st.info(f"CONVOCATION : AG le {dt}. Ordre du jour : {oj}")
        
        else:
            res = st.text_input("Résolution (ex: Travaux Peinture)")
            votes = st.multiselect("Qui vote POUR ?", [c['Nom'] for c in d['copros']])
            if st.button("Enregistrer la décision"):
                total_voix = sum(c['Tantièmes'] for c in d['copros'] if c['Nom'] in votes)
                d['ag_pv'].append({"Date": str(datetime.now().date()), "Sujet": res, "Voix": total_voix})
                save_data(d); st.success(f"Décision actée avec {total_voix} voix.")

    elif menu == "Gestion Copropriétaires":
        st.title("👥 Liste des membres")
        with st.form("new"):
            n, t, c = st.text_input("Nom"), st.number_input("Tantièmes"), st.text_input("Code")
            if st.form_submit_button("Ajouter"):
                d['copros'].append({"Nom": n, "Tantièmes": t, "Code": c})
                save_data(d); st.rerun()
        st.table(d['copros'])

# --- INTERFACE COPROPRIÉTAIRE (EXTRANET) ---
else:
    user = st.session_state.user_info
    st.title(f"🏢 Espace Copropriétaire : {user['Nom']}")
    
    # Dashboard Perso
    t_communes = sum(x['Montant'] for x in d['depenses']) + d['releves_elec']['montant']
    part_commune = (user['Tantièmes'] / d['config']['tantiemes']) * t_communes
    part_eau = d['releves_eau'].get(user['Nom'], 0) * 3.50
    deduction = d['releves_elec']['montant'] if d['releves_elec']['preteur'] == user['Nom'] else 0
    total_net = part_commune + part_eau - deduction

    c1, c2, c3 = st.columns(3)
    c1.metric("À PAYER", f"{total_net:.2f} €")
    c2.metric("Consommation Eau", f"{part_eau:.2f} €")
    c3.metric("Millièmes possédés", user['Tantièmes'])

    tab_c1, tab_c2 = st.tabs(["📖 Détail de mon compte", "📢 Infos & Documents"])
    with tab_c1:
        st.write(f"- Quote-part charges : {part_commune:.2f} €")
        st.write(f"- Facturation eau : {part_eau:.2f} €")
        if deduction > 0:
            st.success(f"Remboursement Électricité : -{deduction:.2f} €")
    
    with tab_c2:
        st.subheader("Derniers messages du Syndic")
        for m in reversed(d['messages']):
            st.info(m['Texte'])
