# Email Sender V2 — Google Sheets Bulk Sender

Application Streamlit permettant d’envoyer automatiquement des emails personnalisés à partir d’un Google Sheet.

Fonctionnalités :

* récupération des destinataires depuis Google Sheets ;
* suppression des doublons ;
* personnalisation des emails ;
* gestion FR / EN ;
* sélection du CV selon la langue ;
* envoi via Gmail SMTP ;
* pause aléatoire de 45 à 90 secondes entre les emails ;
* mise à jour automatique du statut `Envoyé`.

## 1. Prérequis

* Python 3.10+
* `uv`
* compte Gmail
* validation en deux étapes activée sur Gmail
* projet Google Cloud
* Google Sheet contenant les leads

## 2. Installation

Installer `uv` :

```bash
pip install uv
```

Installer les dépendances du projet :

```bash
uv sync
```

## 3. Configuration de Gmail

L’application utilise SMTP Gmail. Le mot de passe Gmail classique ne doit pas être utilisé.

### Activer la validation en deux étapes

[https://myaccount.google.com/security](https://myaccount.google.com/security)

Activez la validation en deux étapes sur votre compte Google.

### Créer un App Password

[https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

Créez un nouveau mot de passe d’application.

Google génère un mot de passe de 16 caractères. Celui-ci sera utilisé par l’application pour se connecter au serveur SMTP Gmail.

## 4. Créer le Google Sheet

Le Google Sheet doit contenir les colonnes suivantes :

```text
Email | Name | Entreprise | Sex | Langue | Envoyé
```

Valeurs attendues :

* `Sex` : `F` ou `M`
* `Langue` : `FR` ou `EN`
* `Envoyé` : `No` ou `Yes`

Les lignes incomplètes sont ignorées.

## 5. Récupérer le Google Sheet ID

L’URL du Google Sheet est de la forme :

```text
https://docs.google.com/spreadsheets/d/GOOGLE_SHEETS_ID/edit
```

Le `GOOGLE_SHEETS_ID` correspond à la partie entre `/d/` et `/edit`.

## 6. Configurer Google Cloud

L’application utilise un **Service Account** pour accéder au Google Sheet.

### Créer un projet

[https://console.cloud.google.com/](https://console.cloud.google.com/)

### Activer Google Sheets API

[https://console.cloud.google.com/apis/library/sheets.googleapis.com](https://console.cloud.google.com/apis/library/sheets.googleapis.com)

Cliquez sur **Enable**.

### Activer Google Drive API

[https://console.cloud.google.com/apis/library/drive.googleapis.com](https://console.cloud.google.com/apis/library/drive.googleapis.com)

Cliquez sur **Enable**.

### Créer le Service Account

[https://console.cloud.google.com/iam-admin/serviceaccounts](https://console.cloud.google.com/iam-admin/serviceaccounts)

Créez un Service Account, puis ouvrez :

```text
Keys → Add Key → Create new key → JSON
```

Téléchargez le fichier JSON et placez-le à la racine du projet sous :

```text
credentials.json
```

### Autoriser le Service Account

Copiez l’adresse email du Service Account.

Dans le Google Sheet :

```text
Partager → Ajouter des personnes
```

Ajoutez cette adresse et attribuez le rôle :

```text
Editor
```

## 7. Configurer `.env`

Créez `.env` à la racine du projet :

```env
GMAIL_ADDRESS=votre.email@gmail.com
APP_PASSWORD=votre_app_password

GOOGLE_SHEETS_ID=votre_google_sheet_id
GOOGLE_CREDS_JSON=credentials.json

SUBJECTS_FR=Premier sujet;Deuxième sujet
SUBJECTS_EN=First subject;Second subject

BODY_FR=Bonjour {salutation} {recipient_name},\n\nVotre message...
BODY_EN=Hello {salutation} {recipient_name},\n\nYour message...
```

### Variables

| Variable            | Description                                    |
| ------------------- | ---------------------------------------------- |
| `GMAIL_ADDRESS`     | Adresse Gmail utilisée pour les envois         |
| `APP_PASSWORD`      | App Password Gmail                             |
| `GOOGLE_SHEETS_ID`  | Identifiant du Google Sheet                    |
| `GOOGLE_CREDS_JSON` | Chemin vers le fichier JSON du Service Account |
| `SUBJECTS_FR`       | Sujets français séparés par `;`                |
| `SUBJECTS_EN`       | Sujets anglais séparés par `;`                 |
| `BODY_FR`           | Template français                              |
| `BODY_EN`           | Template anglais                               |

Les templates peuvent utiliser :

```text
{salutation}
{recipient_name}
{company_name}
```

Le texte entre `**` est automatiquement converti en gras HTML.

## 8. Lancer l’application

```bash
uv run streamlit run main.py
```

## 9. Fonctionnement

L’application :

1. se connecte au Google Sheet ;
2. supprime les doublons d’adresses email ;
3. récupère les lignes avec `Envoyé = No` ;
4. permet d’importer les CV FR et EN ;
5. génère le message personnalisé ;
6. sélectionne le CV correspondant à la langue ;
7. envoie l’email via Gmail SMTP ;
8. passe `Envoyé` de `No` à `Yes` après un envoi réussi ;
9. attend entre 45 et 90 secondes avant l’envoi suivant.

## 10. Sécurité Git

Ajouter dans `.gitignore` :

```gitignore
.env
credentials.json
```

Ne jamais publier ces fichiers sur GitHub : ils contiennent des informations permettant d’accéder aux services utilisés par l’application.

## 11. Arborescence

```text
email-sender/
├── main.py
├── pyproject.toml
├── uv.lock
├── .env
├── credentials.json
├── .gitignore
└── README.md
```
