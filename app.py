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

GMAIL_ADDRESS     = os.getenv("GMAIL_ADDRESS")
APP_PASSWORD      = os.getenv("APP_PASSWORD")
SHEET_ID          = os.getenv("GOOGLE_SHEETS_ID")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")
UI_PASSWORD       = os.getenv("APP_UI_PASSWORD", "")

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
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
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
    subject    = get_subject(lang)
    body       = build_body(lang, salutation, name, company)
    body       = markdown_to_html(body)

    if str(lang).upper() == "FR":
        cv_bytes = cv_fr_bytes
        cv_name  = cv_fr_name
    else:
        cv_bytes = cv_en_bytes
        cv_name  = cv_en_name

    msg = MIMEMultipart("alternative")
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html", "utf-8"))

    attachment = MIMEApplication(cv_bytes, Name=cv_name)
    attachment["Content-Disposition"] = f'attachment; filename="{cv_name}"'
    msg.attach(attachment)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_ADDRESS, APP_PASSWORD)
        server.send_message(msg)


# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Envoi Automatique · CV",
    page_icon="✉️",
    layout="centered",
)

# ── Global CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

.stApp {
    background: #0d0d0f;
    color: #e8e6e1;
}

section[data-testid="stSidebar"] { display: none; }

.block-container {
    max-width: 720px;
    padding: 3rem 2rem 4rem 2rem;
}

h1, h2, h3 { font-family: 'Syne', sans-serif; }

/* ── Login screen ── */
.login-wrap {
    min-height: 80vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    gap: 0;
}

.login-icon {
    font-size: 2.8rem;
    margin-bottom: 1.2rem;
    filter: drop-shadow(0 0 18px rgba(110,231,183,0.35));
}

.login-title {
    font-family: 'Syne', sans-serif;
    font-size: 2rem;
    font-weight: 800;
    color: #f0ede8;
    letter-spacing: -0.03em;
    margin-bottom: 0.3rem;
}

.login-sub {
    color: #555;
    font-size: 0.88rem;
    font-weight: 300;
    margin-bottom: 2rem;
}

.login-error {
    background: rgba(239,68,68,0.07);
    border: 1px solid rgba(239,68,68,0.2);
    border-radius: 10px;
    padding: 0.7rem 1.2rem;
    color: #f87171;
    font-size: 0.85rem;
    margin-top: 0.8rem;
    width: 100%;
    max-width: 360px;
}

/* ── App header ── */
.app-header {
    text-align: center;
    margin-bottom: 3rem;
    padding-bottom: 2rem;
    border-bottom: 1px solid #222;
}

.app-header .badge {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 500;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #6ee7b7;
    background: rgba(110,231,183,0.08);
    border: 1px solid rgba(110,231,183,0.2);
    border-radius: 100px;
    padding: 4px 14px;
    margin-bottom: 1rem;
}

.app-header h1 {
    font-size: 2.4rem;
    font-weight: 800;
    color: #f0ede8;
    line-height: 1.1;
    margin: 0.4rem 0 0.6rem;
    letter-spacing: -0.03em;
}

.app-header p {
    color: #666;
    font-size: 0.95rem;
    font-weight: 300;
    margin: 0;
}

/* ── Sections ── */
.section-label {
    font-size: 0.68rem;
    font-weight: 500;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #555;
    margin-bottom: 0.8rem;
    margin-top: 2.2rem;
}

.card {
    background: #131316;
    border: 1px solid #1e1e23;
    border-radius: 16px;
    padding: 1.6rem 1.8rem;
    margin-bottom: 1rem;
}

/* ── Stats ── */
.stat-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.2rem;
}

.stat-box {
    flex: 1;
    background: #0a0a0c;
    border: 1px solid #1a1a1f;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    text-align: center;
}

.stat-box .value {
    font-family: 'Syne', sans-serif;
    font-size: 1.8rem;
    font-weight: 700;
    color: #6ee7b7;
    line-height: 1;
}

.stat-box .label {
    font-size: 0.72rem;
    color: #555;
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

/* ── Lead list ── */
.lead-item {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 0.75rem 0;
    border-bottom: 1px solid #1a1a1f;
    font-size: 0.88rem;
}

.lead-item:last-child { border-bottom: none; }

.lead-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #6ee7b7;
    flex-shrink: 0;
}

.lead-email { color: #e8e6e1; flex: 1; font-weight: 400; }
.lead-meta  { color: #444; font-size: 0.78rem; }

.lang-badge {
    font-size: 0.65rem;
    padding: 2px 8px;
    border-radius: 100px;
    font-weight: 500;
    letter-spacing: 0.08em;
}

.lang-fr {
    background: rgba(96,165,250,0.1);
    color: #60a5fa;
    border: 1px solid rgba(96,165,250,0.2);
}

.lang-en {
    background: rgba(251,191,36,0.08);
    color: #fbbf24;
    border: 1px solid rgba(251,191,36,0.15);
}

/* ── Misc ── */
.divider {
    border: none;
    border-top: 1px solid #1a1a1f;
    margin: 2rem 0;
}

[data-testid="stFileUploader"] {
    background: #131316;
    border: 1px dashed #2a2a30;
    border-radius: 12px;
    padding: 0.5rem;
}

[data-testid="stFileUploader"]:hover { border-color: #6ee7b7; }

.stProgress > div > div > div {
    background: linear-gradient(90deg, #6ee7b7, #34d399) !important;
    border-radius: 100px;
}

.stProgress > div > div {
    background: #1a1a1f !important;
    border-radius: 100px;
}

.success-box {
    background: rgba(110,231,183,0.05);
    border: 1px solid rgba(110,231,183,0.2);
    border-radius: 12px;
    padding: 1rem 1.4rem;
    color: #6ee7b7;
    font-size: 0.9rem;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}

.warning-box {
    background: rgba(251,191,36,0.05);
    border: 1px solid rgba(251,191,36,0.15);
    border-radius: 12px;
    padding: 1rem 1.4rem;
    color: #fbbf24;
    font-size: 0.9rem;
}

.status-line {
    font-size: 0.85rem;
    color: #888;
    font-style: italic;
    padding: 0.4rem 0;
}
</style>
""", unsafe_allow_html=True)


# ── Auth gate ─────────────────────────────────────────────────────────────────

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="login-icon">🔒</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-title">Accès restreint</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-sub">Entrez le mot de passe pour continuer</div>', unsafe_allow_html=True)

    pwd = st.text_input("Mot de passe", type="password", placeholder="••••••••", label_visibility="collapsed")

    if st.button("Connexion", use_container_width=True, type="primary"):
        if pwd == UI_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.markdown('<div class="login-error">Mot de passe incorrect. Réessayez.</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


# ── Main app (only reached when authenticated) ────────────────────────────────

st.markdown("""
<div class="app-header">
    <div class="badge">Outil de prospection</div>
    <h1>Envoi Automatique</h1>
    <p>Campagne d'emailing personnalisée depuis Google Sheets</p>
</div>
""", unsafe_allow_html=True)

sheet = get_sheet()
clean_duplicates(sheet)

st.markdown('<div class="section-label">Joindre les CV</div>', unsafe_allow_html=True)
col_fr, col_en = st.columns(2)
with col_fr:
    cv_fr_file = st.file_uploader("CV Français", type=["pdf"])
with col_en:
    cv_en_file = st.file_uploader("CV Anglais", type=["pdf"])

st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown('<div class="section-label">Liste des leads</div>', unsafe_allow_html=True)

if "show" not in st.session_state:
    st.session_state.show = False

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("📋  Afficher les leads", use_container_width=True):
        st.session_state.show = True
with col2:
    if st.button("✕  Masquer", use_container_width=True):
        st.session_state.show = False

if st.session_state.show:
    rows = fetch_pending_rows(sheet)

    total_pending = len(rows)
    fr_count = sum(1 for r in rows if str(r.get("Langue", "")).upper() == "FR")
    en_count = total_pending - fr_count

    items_html = ""
    for r in rows:
        lang       = str(r.get("Langue", "")).upper()
        lang_class = "lang-fr" if lang == "FR" else "lang-en"
        lang_label = lang if lang in ("FR", "EN") else lang
        company    = str(r.get("Entreprise", "—"))
        email      = str(r.get("Email", ""))
        items_html += (
            f'<div class="lead-item">'
            f'<div class="lead-dot"></div>'
            f'<div class="lead-email">{email}</div>'
            f'<div class="lead-meta">{company}</div>'
            f'<span class="lang-badge {lang_class}">{lang_label}</span>'
            f'</div>'
        )

    list_block = (
        f'<div class="card">{items_html}</div>'
        if rows
        else '<div class="warning-box">Aucun lead en attente.</div>'
    )

    st.markdown(
        f'<div class="stat-row">'
        f'<div class="stat-box"><div class="value">{total_pending}</div><div class="label">En attente</div></div>'
        f'<div class="stat-box"><div class="value">{fr_count}</div><div class="label">Français</div></div>'
        f'<div class="stat-box"><div class="value">{en_count}</div><div class="label">Anglais</div></div>'
        f'</div>'
        f'{list_block}',
        unsafe_allow_html=True,
    )

st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown('<div class="section-label">Lancement de la campagne</div>', unsafe_allow_html=True)

if st.button("🚀  Lancer l'envoi automatique", use_container_width=True, type="primary"):
    if cv_fr_file is None or cv_en_file is None:
        st.markdown('<div class="warning-box">⚠️ Veuillez uploader les deux CV avant de lancer.</div>', unsafe_allow_html=True)
        st.stop()

    cv_fr_bytes = cv_fr_file.read()
    cv_fr_name  = cv_fr_file.name
    cv_en_bytes = cv_en_file.read()
    cv_en_name  = cv_en_file.name

    rows = fetch_pending_rows(sheet)

    if not rows:
        st.markdown('<div class="warning-box">Aucun email à envoyer.</div>', unsafe_allow_html=True)
        st.stop()

    total    = len(rows)
    progress = st.progress(0)
    status   = st.empty()

    for i, row in enumerate(rows, start=1):
        status.markdown(
            f'<div class="status-line">✉️ Envoi {i}/{total} → {row["Email"]}</div>',
            unsafe_allow_html=True,
        )

        send_email(
            row["Email"], row["Name"], row["Entreprise"],
            row["Sex"], row["Langue"],
            cv_fr_bytes, cv_fr_name,
            cv_en_bytes, cv_en_name,
        )

        mark_sent(sheet, row["_row"])
        progress.progress(i / total)

        if i < total:
            wait_time = random.randint(45, 90)
            status.markdown(
                f'<div class="status-line">⏳ Envoyé {i}/{total} — pause de {wait_time}s avant le prochain…</div>',
                unsafe_allow_html=True,
            )
            time.sleep(wait_time)

    st.markdown(
        '<div class="success-box">✓ Campagne terminée — tous les emails ont été envoyés.</div>',
        unsafe_allow_html=True,
    )