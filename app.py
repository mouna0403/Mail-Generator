import os
import time
import random
import smtplib
import streamlit as st
import gspread
import json
import re

from datetime import datetime, timedelta
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


# ---------------------------------------------------------------------------
# Scheduling helpers
# ---------------------------------------------------------------------------

def is_working_hours(dt: datetime) -> bool:
    """Return True if dt falls within Mon–Fri 09:00–18:00."""
    return dt.weekday() < 5 and 9 <= dt.hour < 18


def next_work_start(dt: datetime) -> datetime:
    """Return the next Mon–Fri 09:00 strictly after dt (or today 09:00 if before 9h)."""
    candidate = dt.replace(hour=9, minute=0, second=0, microsecond=0)
    if dt < candidate and dt.weekday() < 5:
        # Same day, before 9h
        return candidate
    # Move to next day until we hit a weekday
    candidate += timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate


def build_schedule(rows: list, now: datetime) -> list:
    """
    Assign a send datetime to each row.
    If inside working hours: first email = now, gaps = random(45–90s).
    If outside working hours: first email = next_work_start, gaps = random(45–90s).
    Returns list of (row, send_at) tuples.
    """
    if is_working_hours(now):
        first = now
    else:
        first = next_work_start(now)

    schedule = []
    current = first
    for row in rows:
        gap = random.randint(45, 90)
        schedule.append((row, current, gap))
        current = current + timedelta(seconds=gap)

    return schedule


# ---------------------------------------------------------------------------
# Original backend (untouched)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Email Sender", page_icon="✉️", layout="centered")

st.markdown("""
    <style>
        .stApp { background-color: #1a1a1a; }
        .main-header {
            text-align: center; padding: 1.5rem 0;
            margin-bottom: 2rem; border-bottom: 1px solid #333;
        }
        .main-header h1 { color: #ffffff; font-size: 1.8rem; font-weight: 300; margin: 0; letter-spacing: 1px; }
        .main-header p { color: #888; font-size: 0.9rem; margin: 0.5rem 0 0 0; }
        .card { background: #2a2a2a; padding: 1.5rem; border-radius: 8px; margin-bottom: 1.5rem; border: 1px solid #333; }
        .metric { text-align: center; padding: 0.5rem; }
        .metric-number { font-size: 1.8rem; font-weight: 500; color: #ffffff; }
        .metric-label { font-size: 0.8rem; color: #888; margin-top: 0.2rem; }
        .status-box { padding: 0.75rem; border-radius: 6px; margin: 0.5rem 0; text-align: center; font-size: 0.9rem; }
        .success { background: #1a3a2a; color: #7acc8a; border: 1px solid #2a5a3a; }
        .error   { background: #3a1a1a; color: #cc7a7a; border: 1px solid #5a2a2a; }
        .info    { background: #1a2a3a; color: #7aacc8; border: 1px solid #2a4a5a; }
        .wait    { background: #2a2a1a; color: #cccc7a; border: 1px solid #5a5a2a; }
        .scheduled { background: #2a1a3a; color: #b07acc; border: 1px solid #4a2a5a; }
        .terminated { background: #1a3a2a; color: #7acc8a; padding: 1rem; border-radius: 8px; text-align: center; font-weight: 500; margin: 1rem 0; border: 1px solid #2a5a3a; }
        .schedule-table { width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.85rem; }
        .schedule-table th { background: #2a2a2a; color: #aaa; font-weight: 400; padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #444; }
        .schedule-table td { color: #ccc; padding: 0.5rem 0.75rem; border-bottom: 1px solid #333; }
        .schedule-table tr:last-child td { border-bottom: none; }
        .stButton > button { background: #3a3a3a; color: #ffffff; border: 1px solid #555; padding: 0.5rem 2rem; border-radius: 6px; font-weight: 400; width: 100%; transition: all 0.2s; }
        .stButton > button:hover { background: #4a4a4a; border-color: #777; }
        .stTextInput > div > div > input { background: #2a2a2a; border: 1px solid #444; color: #ffffff; border-radius: 6px; }
        .stTextInput > div > div > input:focus { border-color: #666; }
        label, .stMarkdown, .stText { color: #cccccc !important; }
        h1, h2, h3, h4, h5, h6 { color: #ffffff !important; }
        .stFileUploader > div > div > div > div { color: #cccccc !important; }
        .stFileUploader > div > div > div { background: #2a2a2a; border: 1px dashed #555; border-radius: 6px; }
        .dataframe { color: #cccccc !important; }
        .dataframe th { background: #2a2a2a !important; color: #ffffff !important; }
        .dataframe td { background: #1a1a1a !important; color: #cccccc !important; }
        .stAlert { background: #2a2a2a !important; border-color: #444 !important; color: #cccccc !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="main-header">
        <h1>✉️ Email Sender</h1>
        <p>Envoi automatisé d'emails</p>
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
        st.markdown("#### CV FR")
        cv_fr_file = st.file_uploader("PDF", type=["pdf"], key="cv_fr")
    with col2:
        st.markdown("#### CV EN")
        cv_en_file = st.file_uploader("PDF", type=["pdf"], key="cv_en")
    st.markdown('</div>', unsafe_allow_html=True)

if "show" not in st.session_state:
    st.session_state.show = False

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    if st.button("📋 Afficher"):
        st.session_state.show = True
with col2:
    if st.button("✖️ Masquer"):
        st.session_state.show = False

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
    st.markdown(f'<div class="metric"><div class="metric-number">{len(rows)}</div><div class="metric-label">En attente</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric"><div class="metric-number">{total_leads}</div><div class="metric-label">Total</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="metric"><div class="metric-number">{sent_leads}</div><div class="metric-label">Envoyés</div></div>', unsafe_allow_html=True)

if st.session_state.show:
    if rows:
        display_rows = []
        for r in rows:
            display_rows.append({
                "Email": r["Email"],
                "Nom": r["Name"],
                "Entreprise": r["Entreprise"],
                "Sexe": "F" if r["Sex"] == "F" else "M",
                "Langue": r["Langue"]
            })
        st.dataframe(display_rows, use_container_width=True)
    else:
        st.info("Aucun lead en attente")

if st.button("▶️ Envoyer"):
    if cv_fr_file is None or cv_en_file is None:
        st.error("Veuillez télécharger les deux CV")
        st.stop()

    cv_fr_bytes = cv_fr_file.read()
    cv_fr_name  = cv_fr_file.name
    cv_en_bytes = cv_en_file.read()
    cv_en_name  = cv_en_file.name

    rows = fetch_pending_rows(sheet)

    if not rows:
        st.info("Aucun email à envoyer")
        st.stop()

    now = datetime.now()
    schedule = build_schedule(rows, now)
    deferred = not is_working_hours(now)

    # -----------------------------------------------------------------------
    # Show planning table when outside working hours
    # -----------------------------------------------------------------------
    if deferred:
        first_send = schedule[0][1]
        day_labels = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        day_fr = day_labels[first_send.weekday()]
        st.markdown(
            f'<div class="status-box scheduled">🕘 Hors heures de travail — envoi planifié à partir du <b>{day_fr} {first_send.strftime("%d/%m/%Y à %H:%M")}</b></div>',
            unsafe_allow_html=True
        )

        rows_html = ""
        for i, (row, send_at, gap) in enumerate(schedule, start=1):
            gap_str = f"+{gap}s" if i > 1 else "—"
            rows_html += f"""
                <tr>
                    <td>{i}</td>
                    <td>{row['Email']}</td>
                    <td>{row['Name']}</td>
                    <td>{send_at.strftime('%H:%M:%S')}</td>
                    <td>{gap_str}</td>
                </tr>
            """

        st.markdown(f"""
            <table class="schedule-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Email</th>
                        <th>Nom</th>
                        <th>Heure planifiée</th>
                        <th>Intervalle</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        """, unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Sending loop — waits until scheduled time for each email
    # -----------------------------------------------------------------------
    total = len(schedule)
    progress_bar = st.progress(0)
    status_text  = st.empty()
    success_count = 0

    for i, (row, send_at, _gap) in enumerate(schedule, start=1):
        # Wait until it's time
        while True:
            now_loop = datetime.now()
            remaining = (send_at - now_loop).total_seconds()
            if remaining <= 0:
                break
            mins, secs = divmod(int(remaining), 60)
            if mins > 0:
                countdown = f"{mins}m {secs:02d}s"
            else:
                countdown = f"{secs}s"
            status_text.markdown(
                f'<div class="status-box scheduled">🕘 {i}/{total} — {row["Email"]} planifié à {send_at.strftime("%H:%M:%S")} (dans {countdown})</div>',
                unsafe_allow_html=True
            )
            time.sleep(min(remaining, 5))  # refresh every 5s max

        # Send
        try:
            status_text.markdown(
                f'<div class="status-box info">📤 {i}/{total} — Envoi à {row["Email"]}</div>',
                unsafe_allow_html=True
            )
            send_email(
                row["Email"], row["Name"], row["Entreprise"],
                row["Sex"], row["Langue"],
                cv_fr_bytes, cv_fr_name,
                cv_en_bytes, cv_en_name,
            )
            mark_sent(sheet, row["_row"])
            success_count += 1
            progress_bar.progress(i / total)
            status_text.markdown(
                f'<div class="status-box success">✓ {i}/{total} — {row["Email"]} envoyé</div>',
                unsafe_allow_html=True
            )
        except Exception as e:
            status_text.markdown(
                f'<div class="status-box error">✗ {i}/{total} — {row["Email"]} : {str(e)}</div>',
                unsafe_allow_html=True
            )

        # Between emails: the next iteration's send_at already encodes the gap,
        # so we just let the while-loop above handle the wait — no extra sleep needed.

    st.markdown(f"""
        <div class="terminated">
            ✓ Terminé — {success_count}/{total} emails envoyés
        </div>
    """, unsafe_allow_html=True)

    if st.button("🔄 Rafraîchir"):
        st.rerun()