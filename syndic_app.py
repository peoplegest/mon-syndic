import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# --- BASE DE DONNÉES ---
DB_FILE = "data_syndic_master.json"

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {
        "copros": [], "depenses": [], "ag_pv": [], "docs": [], "messages": [],
        "releves_eau": {}, "releves_elec": {"preteur": "", "montant": 0, "kwh": 0, "prix": 0.25},
        "config": {"tantiemes": 1000, "budget_prev": 0}
    }

def save_data(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

d = load_data()

# --- NAVIGATION ---
st.sidebar.title("🏢 Syndic Master Pro")
role = st.sidebar.radio("Sélecteur d'accès", ["Admin: Gestion Syndic", "Extranet Copropriétaires"])

# --- MODE ADMIN ---
if role == "Admin: Gestion Syndic":
    pwd = st.sidebar.text_input("Mot de passe Admin", type="password")
    if pwd == "admin123":
        menu = st.sidebar.selectbox("Menu", ["Tableau de Bord", "Compteurs (Eau/Elec)", "Comptabilité", "AG & Documents"])
        
        if menu == "Tableau de Bord":
            st.title("📊 État de la Copropriété")
            total_communes = sum(x['Montant'] for x in d['depenses']) + d['releves_elec']['montant']
            st.metric("Total Charges à Répartir", f"{total_communes:,.2f} €")
            
            st.subheader("📢 Publier une info aux voisins")
            msg = st.text_area("Message")
            if st.button("Diffuser"):
                d['messages'].append({"Date": str(datetime.now().date()), "Texte": msg})
                save_data(d)
                st.success("Publié !")

        elif menu == "Compteurs (Eau/Elec)":
            st.title("💧 & ⚡ Gestion des compteurs")
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("💧 Relevés Eau")
                p_m3 = st.number_input("Prix m3 (€)", value=3.50)
                for cp in d['copros']:
                    d['releves_eau'][cp['Nom']] = st.number_input(f"Index {cp['Nom']} (m3)", value=d['releves_eau'].get(cp['Nom'], 0))
            
            with col2:
                st.subheader("⚡ Élec Communes (Prêt)")
                preteur = st.selectbox("Prêteur", [c['Nom'] for c in d['copros']])
                kwh = st.number_input("kWh consommés", value=d['releves_elec']['kwh'])
                p_kwh = st.number_input("Prix du kWh", value=d['releves_elec']['prix'])
                if st.button("Calculer & Sauver"):
                    d['releves_elec'] = {"preteur": preteur, "montant": kwh * p_kwh, "kwh": kwh, "prix": p_kwh}
                    save_data(d)
                    st.success("Calcul mis à jour")

        elif menu == "Comptabilité":
            st.title("🧾 Factures Communes")
            with st.form("add"):
                l, m = st.text_input("Libellé"), st.number_input("Montant TTC")
                if st.form_submit_button("Ajouter"):
                    d['depenses'].append({"Date": str(datetime.now().date()), "Libellé": l, "Montant": m})
                    save_data(d); st.rerun()
            st.dataframe(pd.DataFrame(d['depenses']))

        elif menu == "AG & Documents":
            st.title("⚙️ Config & Copropriétaires")
            d['config']['tantiemes'] = st.number_input("Total Tantièmes", value=d['config']['tantiemes'])
            with st.form("new_cp"):
                n, t, c = st.text_input("Nom"), st.number_input("Tantièmes"), st.text_input("Code Extranet")
                if st.form_submit_button("Ajouter Copropriétaire"):
                    d['copros'].append({"Nom": n, "Tantièmes": t, "Code": c})
                    save_data(d); st.rerun()
            st.write("Liste des membres :", d['copros'])
    else:
        st.info("Entrez le mot de passe (défaut: admin123)")

# --- MODE EXTRANET ---
else:
    st.title("🏢 Espace Copropriétaire")
    code = st.text_input("Code d'accès", type="password")
    user = next((c for c in d['copros'] if c["Code"] == code), None)
    
    if user:
        st.header(f"Compte de {user['Nom']}")
        t_communes = sum(x['Montant'] for x in d['depenses']) + d['releves_elec']['montant']
        part_commune = (user['Tantièmes'] / d['config']['tantiemes']) * t_communes
        part_eau = d['releves_eau'].get(user['Nom'], 0) * 3.50
        deduction = d['releves_elec']['montant'] if d['releves_elec']['preteur'] == user['Nom'] else 0
        
        st.metric("TOTAL À PAYER", f"{part_commune + part_eau - deduction:.2f} €")
        
        with st.expander("Détail du calcul"):
            st.write(f"- Charges communes : {part_commune:.2f} €")
            st.write(f"- Consommation eau : {part_eau:.2f} €")
            if deduction > 0: st.write(f"- Remboursement Élec : -{deduction:.2f} €")
        
        st.subheader("📢 Derniers messages")
        for m in reversed(d['messages']): st.info(f"{m['Date']} : {m['Texte']}")
