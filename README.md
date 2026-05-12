# Email Sender V2 — Google Sheets Bulk Sender (Streamlit)

Application Streamlit permettant d’envoyer automatiquement des emails de candidature à partir d’un Google Sheet.  
Elle gère l’envoi en série, la déduplication, le suivi des statuts et l’utilisation de deux CV (FR / EN).

---

## Prérequis

- Python 3.10+
- Compte Gmail
- Validation en deux étapes activée
- Mot de passe d’application Gmail
- Compte Google (Google Sheets + Google Cloud)

---

## 1. Gmail — mot de passe d’application

Gmail n’autorise pas le mot de passe classique pour l’envoi SMTP.

- Activer la validation en deux étapes : https://myaccount.google.com/security  
- Générer un mot de passe d’application : https://myaccount.google.com/apppasswords  
- Choisir “Mail” et copier le code généré

À mettre dans `.env` comme `APP_PASSWORD`.

---

## 2. Google Sheet (structure)

Créer un Google Sheet avec :



Email | Name | Entreprise | Sex | Langue | Envoyé

id="sheet1"

### Valeurs attendues :
- Sex : `M` / `F`
- Langue : `FR` / `EN`
- Envoyé : `No` / `Yes`

---

## 3. Google Cloud — credentials

- Créer un projet : https://console.cloud.google.com/
- Activer les APIs :
  - https://console.cloud.google.com/apis/library/sheets.googleapis.com
  - https://console.cloud.google.com/apis/library/drive.googleapis.com
- Créer un service account : https://console.cloud.google.com/iam-admin/serviceaccounts
- Générer une clé JSON (download)
- Partager le Google Sheet avec l’email du service account (Editor)

---

## 4. Fichier `.env`



GMAIL_ADDRESS=[ton_email@gmail.com](mailto:ton_email@gmail.com)
APP_PASSWORD=ton_app_password

GOOGLE_SHEETS_ID=ton_sheet_id
GOOGLE_CREDS_JSON=credentials.json

id="env1"

---

## 5. Installation

```bash
pip install uv
uv sync
````

---

## 6. Lancement

```bash id="run1"
uv run main.py
```

---

## 7. Fonctionnement de l’application

### 1. Chargement des leads

L’application lit automatiquement le Google Sheet et :

* récupère uniquement les lignes avec `Envoyé = No`
* ignore les lignes incomplètes
* supprime les doublons (un email = une seule ligne conservée)

---

### 2. Upload des CV

Avant de lancer l’envoi, tu dois uploader :

* un CV français
* un CV anglais

Le système choisit automatiquement le bon CV selon la langue du lead :

* FR → CV français
* EN → CV anglais

---

### 3. Envoi des emails

Pour chaque lead :

* un sujet est choisi aléatoirement selon la langue
* un email personnalisé est généré
* le CV correspondant est attaché
* l’email est envoyé via Gmail

---

### 4. Rythme d’envoi

* les emails sont envoyés un par un
* une pause aléatoire est appliquée entre chaque envoi (45 à 90 secondes)
* l’interface affiche le temps d’attente avant chaque email

---

### 5. Suivi

Pendant l’envoi tu vois :

* le numéro d’envoi (`i / total`)
* l’email en cours
* le temps de pause restant

---

### 6. Mise à jour automatique

Après chaque envoi :

* la colonne `Envoyé` passe de `No` à `Yes`

---

## 8. Personnalisation des emails

Tu peux modifier directement dans le code :

* le sujet des emails
* et surtout le contenu du message (body)

Cela te permet d’adapter :

* ton positionnement
* ton ton (plus formel / plus direct)
* ton storytelling
* ou des versions différentes selon les entreprises

---

## 9. Utilisation (workflow utilisateur)

Une fois l’application lancée :

1. Tu ouvres l’interface Streamlit
2. Tu upload ton CV français et anglais
3. Tu vérifies les leads affichés depuis Google Sheets
4. Tu cliques sur “Lancer envoi automatique”
5. L’application :

   * envoie les emails un par un
   * applique les pauses automatiquement
   * met à jour le Google Sheet en temps réel

Tu n’as plus rien à faire pendant l’exécution.

---

## 10. Sécurité

Ne jamais versionner :

```
.env
credentials.json
```

---

## Résumé

* Envoi automatique depuis Google Sheets
* CV dynamique selon langue
* Anti-doublon intégré
* Pause automatique entre emails
* Suivi en temps réel
* Personnalisation facile du message (body)

```
```
