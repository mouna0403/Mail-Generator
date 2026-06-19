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


st.set_page_config(
    page_title="SendPro",
    page_icon="📧",
    layout="centered"
)

st.markdown("""
    <style>
        .stApp {
            background-color: #ffffff;
        }
        .main-header {
            text-align: center;
            padding: 1rem 0;
            margin-bottom: 2rem;
        }
        .main-header h1 {
            color: #1e3c72;
            font-size: 2rem;
            font-weight: 600;
            margin: 0;
        }
        .main-header p {
            color: #666;
            font-size: 1rem;
            margin: 0.5rem 0 0 0;
        }
        .card {
            background: #f8f9fa;
            padding: 1.5rem;
            border-radius: 10px;
            margin-bottom: 1.5rem;
        }
        .metric {
            text-align: center;
            padding: 0.5rem;
        }
        .metric-number {
            font-size: 1.8rem;
            font-weight: 600;
            color: #1e3c72;
        }
        .metric-label {
            font-size: 0.85rem;
            color: #666;
        }
        .status-box {
            padding: 0.75rem;
            border-radius: 8px;
            margin: 0.5rem 0;
            text-align: center;
        }
        .success {
            background: #d4edda;
            color: #155724;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
        }
        .info {
            background: #d1ecf1;
            color: #0c5460;
        }
        .terminated {
            background: #28a745;
            color: white;
            padding: 1rem;
            border-radius: 10px;
            text-align: center;
            font-weight: 600;
            margin: 1rem 0;
        }
        .stButton > button {
            background: #1e3c72;
            color: white;
            border: none;
            padding: 0.5rem 2rem;
            border-radius: 8px;
            font-weight: 500;
            width: 100%;
        }
        .stButton > button:hover {
            background: #2a5298;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="main-header">
        <h1>📧 SendPro</h1>
        <p>Envoi d'emails personnalisés</p>
    </div>
""", unsafe_allow_html=True)

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        pwd = st.text_input("Mot de passe", type="password", placeholder="Entrez votre mot de passe")
        if st.button("Se connecter"):
            if pwd == APP_UI_PASSWORD:
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Mot de passe incorrect")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

sheet = get_sheet()
clean_duplicates(sheet)

with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### CV Français")
        cv_fr_file = st.file_uploader("PDF", type=["pdf"], key="cv_fr")
    with col2:
        st.markdown("#### CV Anglais")
        cv_en_file = st.file_uploader("PDF", type=["pdf"], key="cv_en")
    st.markdown('</div>', unsafe_allow_html=True)

rows = fetch_pending_rows(sheet)

all_data = sheet.get_all_records()
total_leads = 0
sent_leads = 0
for row in all_data:
    if is_complete_row(row):
        total_leads += 1
        if str(row.get("Envoyé", "")).strip().lower() == "yes":
            sent_leads += 1

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"""
        <div class="metric">
            <div class="metric-number">{len(rows)}</div>
            <div class="metric-label">En attente</div>
        </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
        <div class="metric">
            <div class="metric-number">{total_leads}</div>
            <div class="metric-label">Total</div>
        </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
        <div class="metric">
            <div class="metric-number">{sent_leads}</div>
            <div class="metric-label">Envoyés</div>
        </div>
    """, unsafe_allow_html=True)

if st.button("▶️ Envoyer les emails"):
    if cv_fr_file is None or cv_en_file is None:
        st.error("Veuillez télécharger les deux CV")
        st.stop()
    
    cv_fr_bytes = cv_fr_file.read()
    cv_fr_name = cv_fr_file.name
    cv_en_bytes = cv_en_file.read()
    cv_en_name = cv_en_file.name
    
    rows = fetch_pending_rows(sheet)
    
    if not rows:
        st.info("Aucun email à envoyer")
        st.stop()
    
    total = len(rows)
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    success_count = 0
    
    for i, row in enumerate(rows, start=1):
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
            status_text.markdown(f'<div class="status-box success">✅ {i}/{total} - {row["Email"]}</div>', unsafe_allow_html=True)
            
        except Exception as e:
            status_text.markdown(f'<div class="status-box error">❌ {i}/{total} - {row["Email"]} : {str(e)}</div>', unsafe_allow_html=True)
        
        if i < total:
            wait_time = random.randint(45, 90)
            time.sleep(wait_time)
    
    st.markdown(f"""
        <div class="terminated">
            ✅ Terminé ! {success_count}/{total} emails envoyés
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 Rafraîchir"):
        st.rerun()