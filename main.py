import os
import smtplib
import random
import streamlit as st

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate


load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
APP_PASSWORD = os.getenv("APP_PASSWORD")



SUBJECTS_FR = [
    "Candidature spontanée – Data & IA",
    "Candidature – Data Scientist / AI Engineer",
    "Data Science – Candidature spontanée",
]

SUBJECTS_EN = [
    "Spontaneous Application – Data & AI",
    "Application – Data Scientist / AI Engineer",
    "Data Science Profile – Open Application",




# ================= EMAIL LOGIC =================

def get_salutation(language, gender):
    if language == "FR":
        return "Mme" if gender == "F" else "M."
    else:
        return "Ms" if gender == "F" else "Mr"


def build_body(language, salutation, recipient_name, company_name):

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

def send_email(recipient_email, recipient_name, gender, company_name, language, cv_file):

    salutation = get_salutation(language, gender)

    if language == "FR":
        subject = random.choice(SUBJECTS_FR)
    else:
        subject = random.choice(SUBJECTS_EN)

    body = build_body(language, salutation, recipient_name, company_name)

    # LLM reformulation
    #body = reformulate_email(body, language)

    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = recipient_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    if cv_file is not None:
        file_bytes = cv_file.read()
        attachment = MIMEApplication(file_bytes, Name=cv_file.name)
        attachment["Content-Disposition"] = f'attachment; filename="{cv_file.name}"'
        msg.attach(attachment)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_ADDRESS, APP_PASSWORD)
        server.send_message(msg)


# ================= STREAMLIT UI =================

st.title("Email Sender - Candidature")

recipient_name = st.text_input("Nom du destinataire")
recipient_email = st.text_input("Email du destinataire")
company_name = st.text_input("Entreprise")

gender = st.selectbox("Sexe", ["M", "F"])
language = st.selectbox("Langue du mail", ["FR", "EN"])

cv_file = st.file_uploader("CV (PDF)", type=["pdf"])

if st.button("Envoyer"):
    if not all([recipient_name, recipient_email, company_name, cv_file]):
        st.error("Tous les champs sont obligatoires")
    else:
        send_email(
            recipient_email,
            recipient_name,
            gender,
            company_name,
            language,
            cv_file
        )
        st.success("Email envoyé avec succès")