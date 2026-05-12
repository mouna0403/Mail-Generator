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
    required = ["Email", "Name", "Entreprise", "Sex", "Langue", "Envoyé"]

    for c in required:
        if row.get(c) is None or str(row.get(c)).strip() == "":
            return False
    return True


def clean_duplicates(sheet):
    """
    Garde une seule ligne par email :
    - priorité à Envoyé = Yes
    - sinon garde une seule ligne No
    """
    data = sheet.get_all_records()

    best = {}
    to_delete = []

    for i, row in enumerate(data, start=2):
        email = str(row.get("Email", "")).strip().lower()
        status = str(row.get("Envoyé", "")).strip().lower()

        if not email:
            to_delete.append(i)
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


# ================= EMAIL =================

def get_salutation(lang, sex):
    return "Mme" if str(sex).upper() == "F" else "M."


def get_subject(lang):
    return random.choice(SUBJECTS_FR if str(lang).upper() == "FR" else SUBJECTS_EN)


# ====== TON BODY EXACT ======

def build_body(language, salutation, recipient_name, company_name):
    language = str(language).strip().upper()

    github_link = os.getenv("GITHUB_LINK")

    if language == "FR":
        return f"""Bonjour {salutation} {recipient_name},

Je me permets de vous contacter car je m’intéresse à {company_name} et à vos activités autour de la data et de l’IA. Votre parcours a retenu mon attention et j’aimerais en apprendre davantage sur votre expérience ainsi que sur les missions menées.

Je suis récemment diplômée de l’INSA Toulouse en mathématiques appliquées et j’ai réalisé une alternance en data science chez Decathlon, où j’ai travaillé sur des cas d’usage en IA prédictive et générative, en couvrant l’analyse de données, la modélisation ainsi que la mise en production de pipelines data (Airflow), avec déploiement sur GCP et Databricks, en environnement conteneurisé (Docker).

Je souhaite aujourd’hui évoluer vers un poste dans la data (Data Scientist / Data Analyst / Data Engineer). Si mon profil peut correspondre à vos besoins, je serais ravie d’échanger avec vous et de bénéficier de vos retours ou conseils sur votre domaine.

Je me permets de vous joindre mon CV pour plus de détails sur mon parcours.  
Vous pouvez également consulter mes projets sur mon GitHub ({github_link}), notamment une application de système de recommandation intelligent et un assistant documentaire intelligent en constante amélioration.

Merci par avance pour votre temps.

Bien cordialement,
Maïmouna
"""

    else:
        return f"""Hello {salutation} {recipient_name},

I am reaching out because I am interested in {company_name} and your work in data and AI. Your background caught my attention and I would love to learn more about your experience and the missions you are working on.

I recently graduated from INSA Toulouse in applied mathematics and completed a data science apprenticeship at Decathlon, where I worked on predictive and generative AI use cases, covering data analysis, modeling, and production deployment of data pipelines (Airflow), using GCP and Databricks in a containerized environment (Docker).

I am now looking to grow in the data field (Data Scientist / Data Analyst / Data Engineer). If my profile aligns with your needs, I would be glad to discuss with you and get your insights or advice on your work.

I am attaching my CV for more details on my background.  
You can also explore my projects on GitHub ({github_link}), including an intelligent recommendation system and an intelligent document assistant that I continuously improve.

Thank you for your time.

Best regards,
Maïmouna
"""

def send_email(to_email, name, company, sex, lang,
               cv_fr_bytes, cv_fr_name,
               cv_en_bytes, cv_en_name):

    salutation = get_salutation(lang, sex)
    subject = get_subject(lang)
    body = build_body(lang, salutation, name, company)

    if str(lang).upper() == "FR":
        cv_bytes = cv_fr_bytes
        cv_name = cv_fr_name
    else:
        cv_bytes = cv_en_bytes
        cv_name = cv_en_name

    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    attachment = MIMEApplication(cv_bytes, Name=cv_name)
    attachment["Content-Disposition"] = f'attachment; filename="{cv_name}"'
    msg.attach(attachment)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_ADDRESS, APP_PASSWORD)
        server.send_message(msg)


# ================= STREAMLIT =================

st.title("Google Sheet Email Sender V2")

sheet = get_sheet()
clean_duplicates(sheet)

cv_fr_file = st.file_uploader("CV Français (PDF)", type=["pdf"])
cv_en_file = st.file_uploader("CV Anglais (PDF)", type=["pdf"])

if "show" not in st.session_state:
    st.session_state.show = False

col1, col2 = st.columns(2)

with col1:
    if st.button("Afficher les leads"):
        st.session_state.show = True

with col2:
    if st.button("Masquer"):
        st.session_state.show = False

if st.session_state.show:
    rows = fetch_pending_rows(sheet)
    st.write(f"{len(rows)} leads en attente")
    for r in rows:
        st.write(r)

if st.button("Lancer envoi automatique"):

    if cv_fr_file is None or cv_en_file is None:
        st.error("Uploader les deux CV")
        st.stop()

    cv_fr_bytes = cv_fr_file.read()
    cv_fr_name = cv_fr_file.name

    cv_en_bytes = cv_en_file.read()
    cv_en_name = cv_en_file.name

    rows = fetch_pending_rows(sheet)

    if not rows:
        st.info("Aucun email")
        st.stop()

    total = len(rows)
    progress = st.progress(0)
    status = st.empty()

    for i, row in enumerate(rows, start=1):

        status.write(f"Envoi {i}/{total} → {row['Email']}")

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
        progress.progress(i / total)

        if i < total:
            wait_time = random.randint(45, 90)
            status.write(f"Envoyé {i}/{total} → pause {wait_time}s")
            time.sleep(wait_time)

    st.success("Terminé")