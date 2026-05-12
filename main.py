import os
import time
import random
import smtplib
import streamlit as st
import gspread

from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


load_dotenv()

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
APP_PASSWORD = os.getenv("APP_PASSWORD")
SHEET_ID = os.getenv("GOOGLE_SHEETS_ID")
CREDS_FILE = os.getenv("GOOGLE_CREDS_JSON")


SUBJECTS_FR = [
    "Candidature spontanée – Data & IA",
    "Candidature – Data Scientist / AI Engineer",
    "Data Science – Candidature spontanée",
]

SUBJECTS_EN = [
    "Spontaneous Application – Data & AI",
    "Application – Data Scientist / AI Engineer",
    "Data Science Profile – Open Application",
]


# ================= GOOGLE SHEETS =================

def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = Credentials.from_service_account_file(
        CREDS_FILE,
        scopes=scopes
    )
    client = gspread.authorize(creds)

    return client.open_by_key(SHEET_ID).sheet1


def is_complete_row(row):
    """
    Vérifie que toutes les colonnes obligatoires sont remplies.
    Colonnes attendues :
    Email | Name | Entreprise | Sex | Langue | Envoyé
    """
    required_columns = [
        "Email",
        "Name",
        "Entreprise",
        "Sex",
        "Langue",
        "Envoyé",
    ]

    for column in required_columns:
        value = row.get(column, "")
        if value is None or str(value).strip() == "":
            return False

    return True


def clean_duplicate_pending_rows(sheet):
    """
    Si une même adresse email apparaît plusieurs fois et qu'au moins une ligne
    possède déjà Envoyé = Yes, alors toutes les autres lignes avec Envoyé = No
    sont automatiquement supprimées.
    """
    data = sheet.get_all_records()

    # Emails ayant déjà reçu un email
    sent_emails = set()

    for row in data:
        email = str(row.get("Email", "")).strip().lower()
        sent_status = str(row.get("Envoyé", "")).strip().lower()

        if email and sent_status == "yes":
            sent_emails.add(email)

    # Lignes à supprimer
    rows_to_delete = []

    for i, row in enumerate(data, start=2):  # ligne 1 = header
        email = str(row.get("Email", "")).strip().lower()
        sent_status = str(row.get("Envoyé", "")).strip().lower()

        if email in sent_emails and sent_status == "no":
            rows_to_delete.append(i)

    # Suppression de bas en haut
    for row_index in reversed(rows_to_delete):
        sheet.delete_rows(row_index)

    return len(rows_to_delete)


def fetch_pending_rows(sheet):
    """
    Sélectionne uniquement les lignes :
    - complètement remplies
    - avec Envoyé = No
    """
    data = sheet.get_all_records()
    pending = []

    for i, row in enumerate(data, start=2):  # ligne 1 = header
        if not is_complete_row(row):
            continue

        if str(row["Envoyé"]).strip().lower() != "no":
            continue

        row["_row"] = i
        pending.append(row)

    return pending


def mark_sent(sheet, row_index):
    # Colonne 6 = "Envoyé"
    sheet.update_cell(row_index, 6, "Yes")


# ================= EMAIL HELPERS =================

def get_salutation(language, gender):
    language = str(language).strip().upper()
    gender = str(gender).strip().upper()

    if language == "FR":
        return "Mme" if gender == "F" else "M."
    else:
        return "Ms" if gender == "F" else "Mr"


def get_subject(language):
    language = str(language).strip().upper()

    if language == "FR":
        return random.choice(SUBJECTS_FR)

    return random.choice(SUBJECTS_EN)


def build_body(language, salutation, recipient_name, company_name):
    language = str(language).strip().upper()

    if language == "FR":
        return f"""Bonjour {salutation} {recipient_name},

Je me permets de vous contacter car je m’intéresse à {company_name} et à vos activités autour de la data et de l’IA. Votre parcours a retenu mon attention et j’aimerais en apprendre davantage sur votre expérience ainsi que sur les missions menées.

Je suis récemment diplômée de l’INSA Toulouse en mathématiques appliquées et j’ai réalisé une alternance en data science chez Decathlon, où j’ai travaillé sur des cas d’usage en IA prédictive et générative, en couvrant l’analyse de données, la modélisation ainsi que la mise en production de pipelines data (Airflow), avec déploiement sur GCP et Databricks, en environnement conteneurisé (Docker).

Je souhaite aujourd’hui évoluer vers un poste dans la data (Data Scientist / Data Analyst / Data Engineer). Si vous pensez que mon profil pourrait correspondre à l’esprit et aux attentes de vos équipes, je serais ravie de pouvoir échanger avec vous et, le moment venu, de bénéficier de vos conseils, voire d’une recommandation lorsqu’une opportunité se présentera.

Je peux bien sûr vous transmettre mon CV si besoin.

Merci par avance pour votre temps.

Bien cordialement,
Maïmouna
"""
    else:
        return f"""Hello {salutation} {recipient_name},

I am reaching out because I am interested in {company_name} and your work in data and AI. Your background caught my attention and I would love to learn more about your experience and the missions you are working on.

I recently graduated from INSA Toulouse in applied mathematics and completed a data science apprenticeship at Decathlon, where I worked on predictive and generative AI use cases, covering data analysis, modeling, and production deployment of data pipelines (Airflow), using GCP and Databricks in a containerized environment (Docker).

I am now looking to grow in the data field (Data Scientist / Data Analyst / Data Engineer). If you think my profile could match your team’s needs, I would be glad to discuss with you and possibly get your advice or recommendation when opportunities arise.

I can also share my CV if needed.

Thank you for your time.

Best regards,
Maïmouna
"""


# ================= EMAIL SENDER =================

def send_email(
    to_email,
    name,
    company,
    sex,
    lang,
    cv_bytes,
    cv_filename,
):
    salutation = get_salutation(lang, sex)
    subject = get_subject(lang)
    body = build_body(lang, salutation, name, company)

    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    # Pièce jointe CV
    attachment = MIMEApplication(cv_bytes, Name=cv_filename)
    attachment["Content-Disposition"] = (
        f'attachment; filename="{cv_filename}"'
    )
    msg.attach(attachment)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_ADDRESS, APP_PASSWORD)
        server.send_message(msg)


# ================= STREAMLIT UI =================

st.title("Google Sheet Email Sender")

# État d'affichage des leads
if "show_leads" not in st.session_state:
    st.session_state.show_leads = False

# Upload du CV
cv_file = st.file_uploader("CV (PDF)", type=["pdf"])

# Connexion au Google Sheet
sheet = get_sheet()

# Nettoyage automatique des doublons :
# si un email a déjà un "Yes", toutes les lignes "No" du même email sont supprimées.
deleted_count = clean_duplicate_pending_rows(sheet)

if deleted_count > 0:
    st.warning(
        f"{deleted_count} ligne(s) en doublon ont été supprimées "
        f"car un email avait déjà été envoyé."
    )

# Boutons Afficher / Masquer
col1, col2 = st.columns(2)

with col1:
    if st.button("Afficher les leads à envoyer"):
        st.session_state.show_leads = True

with col2:
    if st.button("Masquer les leads"):
        st.session_state.show_leads = False

# Affichage des leads
if st.session_state.show_leads:
    rows = fetch_pending_rows(sheet)

    st.write(f"{len(rows)} emails en attente")

    for row in rows:
        st.write({
            "Email": row["Email"],
            "Name": row["Name"],
            "Entreprise": row["Entreprise"],
            "Sex": row["Sex"],
            "Langue": row["Langue"],
            "Envoyé": row["Envoyé"],
        })

# Envoi automatique
if st.button("Lancer envoi automatique"):

    if cv_file is None:
        st.error("Veuillez uploader votre CV avant de lancer l'envoi.")
        st.stop()

    cv_bytes = cv_file.read()
    cv_filename = cv_file.name

    rows = fetch_pending_rows(sheet)

    if not rows:
        st.info("Aucun email valide à envoyer.")
        st.stop()

    st.write(f"Envoi de {len(rows)} emails")

    progress = st.progress(0)
    status = st.empty()

    for index, row in enumerate(rows, start=1):
        send_email(
            to_email=row["Email"],
            name=row["Name"],
            company=row["Entreprise"],
            sex=row["Sex"],
            lang=row["Langue"],
            cv_bytes=cv_bytes,
            cv_filename=cv_filename,
        )

        # Marquer comme envoyé
        mark_sent(sheet, row["_row"])

        progress.progress(index / len(rows))
        status.write(
            f"Envoyé à {row['Email']} ({index}/{len(rows)})"
        )

        # Pause aléatoire entre 45 et 90 secondes
        if index < len(rows):
            wait_time = random.randint(45, 90)
            st.write(f"Pause de {wait_time} secondes...")
            time.sleep(wait_time)

    # Masquer automatiquement les leads
    st.session_state.show_leads = False

    st.success("Envoi terminé avec succès.")