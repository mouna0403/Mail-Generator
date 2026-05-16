import os
import time
import random
import smtplib
import streamlit as st
import gspread
import json

from google.oauth2.service_account import Credentials

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


# ================= SECURITY =================

PASSWORD = st.secrets["APP_UI_PASSWORD"]

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    pwd = st.text_input("Mot de passe", type="password")

    if pwd and pwd == PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    else:
        st.stop()


# ================= SECRETS =================

GMAIL_ADDRESS = st.secrets["GMAIL_ADDRESS"]
APP_PASSWORD = st.secrets["APP_PASSWORD"]
SHEET_ID = st.secrets["GOOGLE_SHEETS_ID"]

SUBJECTS_FR = st.secrets["SUBJECTS_FR"].split(";")
SUBJECTS_EN = st.secrets["SUBJECTS_EN"].split(";")

BODY_FR = st.secrets["BODY_FR"]
BODY_EN = st.secrets["BODY_EN"]

CREDS_FILE = st.secrets["GOOGLE_CREDS_JSON"]


# ================= GOOGLE SHEETS AUTH =================

def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds_dict = json.loads(st.secrets["GOOGLE_CREDS_JSON"])

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=scopes
    )

    client = gspread.authorize(creds)
    return client.open_by_key(st.secrets["GOOGLE_SHEETS_ID"]).sheet1


# ================= LOGIC =================

def is_complete_row(row):
    required = ["Email", "Name", "Entreprise", "Sex", "Langue", "Envoyé"]
    return all(str(row.get(c, "")).strip() != "" for c in required)


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


# ================= STREAMLIT UI =================

st.title("Google Sheet Email Sender V2")

sheet = get_sheet()

cv_fr_file = st.file_uploader("CV Français (PDF)", type=["pdf"])
cv_en_file = st.file_uploader("CV Anglais (PDF)", type=["pdf"])

if st.button("Lancer envoi automatique"):

    if cv_fr_file is None or cv_en_file is None:
        st.error("Uploader les deux CV")
        st.stop()

    cv_fr_bytes = cv_fr_file.read()
    cv_en_bytes = cv_en_file.read()

    rows = fetch_pending_rows(sheet)

    if not rows:
        st.info("Aucun email")
        st.stop()

    total = len(rows)
    progress = st.progress(0)

    for i, row in enumerate(rows, start=1):

        send_email(
            row["Email"],
            row["Name"],
            row["Entreprise"],
            row["Sex"],
            row["Langue"],
            cv_fr_bytes,
            cv_fr_file.name,
            cv_en_bytes,
            cv_en_file.name,
        )

        mark_sent(sheet, row["_row"])
        progress.progress(i / total)

        if i < total:
            time.sleep(random.randint(45, 90))

    st.success("Terminé")