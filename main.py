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

SUBJECTS_FR = [s.strip() for s in os.getenv("SUBJECTS_FR", "").split(";") if s.strip()]
SUBJECTS_EN = [s.strip() for s in os.getenv("SUBJECTS_EN", "").split(";") if s.strip()]

BODY_FR = os.getenv("BODY_FR")
BODY_EN = os.getenv("BODY_EN")


# ================= GOOGLE SHEETS =================

@st.cache_resource
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


# ================= EMAIL =================

def get_salutation(lang, sex):
    lang = str(lang).strip().upper()
    sex = str(sex).strip().upper()

    if lang == "FR":
        return "Mme" if sex == "F" else "M."
    else:
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
    else:
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