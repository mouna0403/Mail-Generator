````markdown
# Email Sender V2 — Google Sheets Bulk Sender (Streamlit)

Application Streamlit permettant d’envoyer automatiquement des emails de candidature personnalisés à partir d’un Google Sheet, avec gestion de file d’attente, déduplication, mise à jour automatique du statut et envoi séquentiel contrôlé.

---

## Prérequis

- Python 3.10+
- Compte Gmail
- Validation en deux étapes activée
- Mot de passe d’application Gmail
- Google Cloud Project avec :
  - Google Sheets API activée
  - Google Drive API activée
- Service Account Google (fichier JSON)

---

## 1. Structure du Google Sheet

Le fichier doit contenir exactement ces colonnes :

```text
Email | Name | Entreprise | Sex | Langue | Envoyé
````

### Valeurs attendues

* Sex : `M` / `F`
* Langue : `FR` / `EN`
* Envoyé : `Yes` / `No`

---

## 2. Accès Google Sheets

### Service Account

* Créer un service account dans Google Cloud
* Télécharger le fichier `.json`

### Partage du Google Sheet

Partager le Google Sheet avec l’email du service account (champ `client_email` du JSON) avec le rôle **Editor**.

---

## 3. Installation des dépendances

```bash
pip install uv
uv sync
```

---

## 4. Configuration `.env`

Créer un fichier `.env` à la racine :

```env
GMAIL_ADDRESS=votre.adresse@gmail.com
APP_PASSWORD=votre_app_password

GOOGLE_SHEETS_ID=your_google_sheet_id
GOOGLE_CREDS_JSON=credentials.json
```

---

## 5. Lancer l’application

```bash
uv run main.py
```

---

## 6. Fonctionnement global

### Chargement des données

L’application lit automatiquement le Google Sheet et sélectionne uniquement les lignes :

* complètes (aucune colonne vide)
* avec `Envoyé = No`

---

### Déduplication automatique

Avant affichage et envoi :

* si un email a déjà `Envoyé = Yes`
* toutes les autres lignes associées avec `No` sont supprimées automatiquement

Objectif : éviter tout double envoi accidentel.

---

### Envoi des emails

Pour chaque lead :

* génération du sujet aléatoire selon la langue
* génération de la civilité :

  * FR → Mme / M.
  * EN → Ms / Mr
* insertion du contenu personnalisé
* ajout automatique du CV en pièce jointe
* envoi via SMTP Gmail

---

### Contrôle du rythme d’envoi

* envoi séquentiel
* pause aléatoire entre chaque email :

  * 45 à 90 secondes

---

### Mise à jour du Google Sheet

Après chaque envoi :

* `Envoyé` passe de `No` → `Yes`

---

## 7. Interface Streamlit

Fonctionnalités disponibles :

* upload du CV (une seule fois)
* affichage des leads filtrés
* masquage de la liste des leads
* lancement de l’envoi automatique
* suivi de progression en temps réel

---

## 8. Logique métier

### Sélection des leads

* uniquement lignes complètes
* uniquement `Envoyé = No`

### Sécurité anti-doublon

* suppression des doublons historiques
* protection contre ré-ajout manuel d’un contact déjà traité

---

## 9. Arborescence du projet

```text
email-sender/
├── main.py
├── pyproject.toml
├── .env
├── credentials.json
└── README.md
```

---

## 10. Sécurité

Ne jamais versionner :

```gitignore
.env
credentials.json
```

---

## 11. Dépannage

### Aucun email envoyé

* vérifier `Envoyé = No`
* vérifier colonnes complètes

### Erreur Google Sheets

* vérifier partage avec service account
* vérifier `GOOGLE_SHEETS_ID`

### Erreur Gmail SMTP

* utiliser un mot de passe d’application Gmail (pas le mot de passe classique)

---

## 12. Évolutions possibles

* bouton pause / reprise d’envoi
* file d’envoi persistante (queue)
* logs d’erreurs dans le Google Sheet
* retry automatique en cas d’échec SMTP
* dashboard CRM des candidatures

```
```
