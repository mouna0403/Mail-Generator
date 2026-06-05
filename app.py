import os
import time
import random
import smtplib
import streamlit as st
import gspread
import json
import re

from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

load_dotenv()

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
APP_PASSWORD = os.getenv("APP_PASSWORD")
APP_UI_PASSWORD = os.getenv("APP_UI_PASSWORD")
SHEET_ID = os.getenv("GOOGLE_SHEETS_ID")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

SUBJECTS_FR = [s.strip() for s in os.getenv("SUBJECTS_FR", "").split(";") if s.strip()]
SUBJECTS_EN = [s.strip() for s in os.getenv("SUBJECTS_EN", "").split(";") if s.strip()]

BODY_FR = os.getenv("BODY_FR")
BODY_EN = os.getenv("BODY_EN")


def markdown_to_html(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = text.replace("\n\n", "<br><br>")
    text = text.replace("\n", "<br>")
    return text


@st.cache_resource
def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds_info = json.loads(GOOGLE_CREDS_JSON)

    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=scopes
    )

    client = gspread.authorize(creds)

    return client.open_by_key(SHEET_ID).sheet1


def is_complete_row(row):
    required = ["Email", "Name", "Entreprise", "Sex", "Langue", "Envoyé"]
    for c in required:
        if row.get(c) is None or str(row.get(c)).strip() == "":
            return False
    return True


def clean_duplicates(sheet):
    data = sheet.get_all_records()

    best = {}
    to_delete = []

    for i, row in enumerate(data, start=2):
        email = str(row.get("Email", "")).strip().lower()
        status = str(row.get("Envoyé", "")).strip().lower()

        if not email:
            continue

        if email not in best:
            best[email] = (i, status)
        else:
            prev_i, prev_status = best[email]

            if status == "yes" and prev_status != "yes":
                to_delete.append(prev_i)
                best[email] = (i, status)
            else:
                to_delete.append(i)

    for r in reversed(to_delete):
        sheet.delete_rows(r)


def fetch_pending_rows(sheet):
    data = sheet.get_all_records()
    rows = []

    for i, row in enumerate(data, start=2):
        if not is_complete_row(row):
            continue

        if str(row["Envoyé"]).strip().lower() != "no":
            continue

        row["_row"] = i
        rows.append(row)

    return rows


def mark_sent(sheet, row_index):
    sheet.update_cell(row_index, 6, "Yes")


def get_salutation(lang, sex):
    lang = str(lang).strip().upper()
    sex = str(sex).strip().upper()

    if lang == "FR":
        return "Mme" if sex == "F" else "M."
    return "Ms." if sex == "F" else "Mr."


def get_subject(lang):
    return random.choice(SUBJECTS_FR if str(lang).upper() == "FR" else SUBJECTS_EN)


def build_body(language, salutation, recipient_name, company_name):
    language = str(language).strip().upper()

    if language == "FR":
        return BODY_FR.format(
            salutation=salutation,
            recipient_name=recipient_name,
            company_name=company_name
        )

    return BODY_EN.format(
        salutation=salutation,
        recipient_name=recipient_name,
        company_name=company_name
    )


def send_email(to_email, name, company, sex, lang,
               cv_fr_bytes, cv_fr_name,
               cv_en_bytes, cv_en_name):

    salutation = get_salutation(lang, sex)
    subject = get_subject(lang)
    body = markdown_to_html(build_body(lang, salutation, name, company))

    if str(lang).upper() == "FR":
        cv_bytes = cv_fr_bytes
        cv_name = cv_fr_name
    else:
        cv_bytes = cv_en_bytes
        cv_name = cv_en_name

    msg = MIMEMultipart("alternative")
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "html", "utf-8"))

    attachment = MIMEApplication(cv_bytes, Name=cv_name)
    attachment["Content-Disposition"] = f'attachment; filename="{cv_name}"'
    msg.attach(attachment)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_ADDRESS, APP_PASSWORD)
        server.send_message(msg)


# Configuration de la page
st.set_page_config(
    page_title="SendPro - Envoi d'emails personnalisés",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personnalisé - tout en noir sur fond clair
st.markdown("""
    <style>
        /* Style général - fond blanc cassé */
        .stApp {
            background-color: #f5f5f5;
        }
        
        /* Container principal */
        .main-header {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            padding: 2rem;
            border-radius: 15px;
            margin-bottom: 2rem;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .main-header h1 {
            color: white;
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            font-weight: 700;
        }
        
        .main-header p {
            color: rgba(255,255,255,0.9);
            font-size: 1.1rem;
        }
        
        /* Cartes - fond blanc, texte noir */
        .card {
            background: white;
            padding: 1.5rem;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            margin-bottom: 1.5rem;
            transition: transform 0.3s ease;
            color: #000000;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        }
        
        .card-title {
            font-size: 1.3rem;
            font-weight: 600;
            color: #1e3c72;
            margin-bottom: 1rem;
            border-bottom: 2px solid #1e3c72;
            padding-bottom: 0.5rem;
        }
        
        /* Métriques - fond bleu foncé, texte blanc */
        .metric-card {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 1rem;
            border-radius: 10px;
            text-align: center;
            margin: 0.5rem 0;
        }
        
        .metric-number {
            font-size: 2rem;
            font-weight: 700;
        }
        
        .metric-label {
            font-size: 0.9rem;
            opacity: 0.9;
        }
        
        /* Message de succès - vert clair, texte vert foncé */
        .success-message {
            background: #d4edda;
            color: #155724;
            padding: 1rem;
            border-radius: 10px;
            border-left: 4px solid #28a745;
            margin: 1rem 0;
        }
        
        /* Message d'erreur - rouge clair, texte rouge foncé */
        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 1rem;
            border-radius: 10px;
            border-left: 4px solid #dc3545;
            margin: 1rem 0;
        }
        
        /* Message info - bleu clair, texte bleu foncé */
        .info-message {
            background: #d1ecf1;
            color: #0c5460;
            padding: 1rem;
            border-radius: 10px;
            border-left: 4px solid #17a2b8;
            margin: 1rem 0;
        }
        
        /* Uploader */
        .upload-container {
            border: 2px dashed #1e3c72;
            border-radius: 10px;
            padding: 1rem;
            text-align: center;
        }
        
        /* Inputs */
        .stTextInput > div > div > input {
            border-radius: 10px;
            border: 1px solid #ddd;
        }
        
        /* Dataframe */
        .dataframe {
            font-size: 0.9rem;
        }
        
        /* État terminé */
        .terminated-message {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 15px;
            text-align: center;
            margin: 1rem 0;
            font-size: 1.2rem;
            font-weight: 600;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        /* Texte de statut */
        .status-text {
            font-weight: 500;
            padding: 0.5rem;
            border-radius: 8px;
        }
        
        .status-success {
            background-color: #d4edda;
            color: #155724;
        }
        
        .status-error {
            background-color: #f8d7da;
            color: #721c24;
        }
        
        .status-info {
            background-color: #d1ecf1;
            color: #0c5460;
        }
        
        /* Labels en noir */
        label, .stMarkdown, .stText {
            color: #000000 !important;
        }
        
        /* Titres en noir */
        h1, h2, h3, h4, h5, h6 {
            color: #1e3c72 !important;
        }
        
        /* Boutons - bleu foncé */
        .stButton > button {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            border: none;
            padding: 0.6rem 1.5rem;
            font-weight: 600;
            border-radius: 10px;
            transition: all 0.3s ease;
            width: 100%;
            font-size: 1rem;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(30, 60, 114, 0.4);
        }
        
        /* File uploader texte */
        .stFileUploader > div > div > div > div {
            color: #000000 !important;
        }
    </style>
""", unsafe_allow_html=True)

# En-tête principal
st.markdown("""
    <div class="main-header">
        <h1>📧 SendPro</h1>
        <p>Solution professionnelle d'envoi d'emails personnalisés</p>
    </div>
""", unsafe_allow_html=True)

# Gestion de l'authentification
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div class="card">
                <div class="card-title">🔐 Accès sécurisé</div>
        """, unsafe_allow_html=True)
        pwd = st.text_input("Mot de passe", type="password", placeholder="Entrez votre mot de passe")
        if st.button("Se connecter", use_container_width=True):
            if pwd == APP_UI_PASSWORD:
                st.session_state.auth = True
                st.rerun()
            else:
                st.markdown('<div class="error-message">❌ Mot de passe incorrect</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# Contenu principal après authentification
sheet = get_sheet()
clean_duplicates(sheet)

# Deux colonnes pour la section CV
st.markdown("### 📎 Téléchargement des CV")
col1, col2 = st.columns(2)

with col1:
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 🇫🇷 CV Français")
        cv_fr_file = st.file_uploader("Format PDF uniquement", type=["pdf"], key="cv_fr")
        st.markdown('</div>', unsafe_allow_html=True)

with col2:
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 🇬🇧 CV Anglais")
        cv_en_file = st.file_uploader("Format PDF uniquement", type=["pdf"], key="cv_en")
        st.markdown('</div>', unsafe_allow_html=True)

# Section des leads
if "show" not in st.session_state:
    st.session_state.show = False

st.markdown("### 📊 Gestion des leads")
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    if st.button("📋 Afficher les leads", use_container_width=True):
        st.session_state.show = True

with col2:
    if st.button("🙈 Masquer", use_container_width=True):
        st.session_state.show = False

if st.session_state.show:
    rows = fetch_pending_rows(sheet)
    
    # Métriques
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-number">{len(rows)}</div>
                <div class="metric-label">Leads en attente</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_leads = len(sheet.get_all_records())
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-number">{total_leads}</div>
                <div class="metric-label">Total des leads</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        sent_leads = total_leads - len(rows)
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-number">{sent_leads}</div>
                <div class="metric-label">Emails envoyés</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Affichage des leads dans un tableau stylisé
    if rows:
        st.markdown("#### 📋 Détail des leads à contacter")
        display_rows = []
        for r in rows:
            display_rows.append({
                "Email": r["Email"],
                "Nom": r["Name"],
                "Entreprise": r["Entreprise"],
                "Sexe": "Féminin" if r["Sex"] == "F" else "Masculin",
                "Langue": r["Langue"]
            })
        st.dataframe(display_rows, use_container_width=True)
    else:
        st.markdown('<div class="info-message">✨ Aucun lead en attente d\'envoi</div>', unsafe_allow_html=True)

# Section d'envoi
st.markdown("### 🚀 Envoi des emails")

if st.button("▶️ Lancer l'envoi automatique", use_container_width=True):
    
    if cv_fr_file is None or cv_en_file is None:
        st.markdown('<div class="error-message">⚠️ Veuillez télécharger les deux CV (Français et Anglais) avant de lancer l\'envoi</div>', unsafe_allow_html=True)
        st.stop()
    
    cv_fr_bytes = cv_fr_file.read()
    cv_fr_name = cv_fr_file.name
    
    cv_en_bytes = cv_en_file.read()
    cv_en_name = cv_en_file.name
    
    rows = fetch_pending_rows(sheet)
    
    if not rows:
        st.markdown('<div class="info-message">ℹ️ Aucun email à envoyer</div>', unsafe_allow_html=True)
        st.stop()
    
    total = len(rows)
    
    # Affichage de la progression
    st.markdown("#### 📊 Progression de l'envoi")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Container pour les logs
    log_container = st.container()
    
    success_count = 0
    
    for i, row in enumerate(rows, start=1):
        
        with log_container:
            st.markdown(f'<div class="status-info">🔄 Envoi en cours... ({i}/{total}) → {row["Email"]}</div>', unsafe_allow_html=True)
        
        try:
            send_email(
                row["Email"],
                row["Name"],
                row["Entreprise"],
                row["Sex"],
                row["Langue"],
                cv_fr_bytes,
                cv_fr_name,
                cv_en_bytes,
                cv_en_name,
            )
            
            mark_sent(sheet, row["_row"])
            success_count += 1
            
            progress_bar.progress(i / total)
            status_text.markdown(f'<div class="status-success">✅ Envoyé ({i}/{total}) → {row["Email"]} - {row["Name"]}</div>', unsafe_allow_html=True)
            
        except Exception as e:
            status_text.markdown(f'<div class="status-error">❌ Erreur ({i}/{total}) → {row["Email"]} : {str(e)}</div>', unsafe_allow_html=True)
        
        if i < total:
            wait_time = random.randint(45, 90)
            status_text.markdown(f'<div class="status-info">⏱️ Pause de {wait_time} secondes avant le prochain envoi...</div>', unsafe_allow_html=True)
            time.sleep(wait_time)
    
    # Message de fin "Terminé" après tous les envois
    st.markdown(f"""
        <div class="terminated-message">
            ✅ TERMINÉ !<br>
            📧 {success_count} email(s) envoyé(s) avec succès sur {total}
        </div>
    """, unsafe_allow_html=True)
    
    # Option pour rafraîchir l'affichage
    if st.button("🔄 Rafraîchir", use_container_width=True):
        st.rerun()