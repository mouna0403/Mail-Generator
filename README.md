# Email Sender V2 — Google Sheets Bulk Sender (Streamlit)

Application Streamlit permettant d’envoyer automatiquement des emails de candidature personnalisés à partir d’un Google Sheet, avec gestion de file d’attente, déduplication avancée, suppression des doublons, gestion multi-CV (FR/EN), et envoi séquentiel contrôlé avec pause aléatoire.

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

Le Google Sheet doit contenir exactement ces colonnes :

```text
Email | Name | Entreprise | Sex | Langue | Envoyé
````

### Valeurs attendues

* Sex : `M` / `F`
* Langue : `FR` / `EN`
* Envoyé : `Yes` / `No`

---

## 2. Nettoyage automatique des données

Avant chaque exécution :

### Déduplication intelligente

* 1 seul email conservé par personne
* Si doublon :

  * priorité à `Envoyé = Yes`
  * sinon conservation d’une seule ligne `No`
* suppression automatique des doublons inutiles dans le Google Sheet

---

## 3. Sélection des leads

Seules les lignes sont prises en compte si :

* toutes les colonnes sont remplies
* `Envoyé = No`
* email non supprimé par la déduplication

---

## 4. Gestion des CV (nouvelle fonctionnalité)

L’application utilise **2 CV distincts** :

* CV Français → utilisé pour `Langue = FR`
* CV Anglais → utilisé pour `Langue = EN`

Chaque email reçoit automatiquement le CV correspondant à sa langue.

---

## 5. Accès Google Sheets

### Service Account

* Créer un service account dans Google Cloud
* Télécharger le fichier `.json`

### Partage du Google Sheet

Partager le Google Sheet avec l’email du service account (`client_email`) avec rôle **Editor**.

---

## 6. Installation des dépendances

```bash
pip install uv
uv sync
```

---

## 7. Configuration `.env`

Créer un fichier `.env` :

```env
GMAIL_ADDRESS=votre.adresse@gmail.com
APP_PASSWORD=votre_app_password

GOOGLE_SHEETS_ID=your_google_sheet_id
GOOGLE_CREDS_JSON=credentials.json
```

---

## 8. Lancement de l’application

```bash
uv run main.py
```

---

## 9. Fonctionnement global

### Chargement des données

* lecture du Google Sheet
* suppression des doublons
* filtrage des leads `Envoyé = No`

---

### Génération des emails

Pour chaque lead :

* sujet aléatoire selon la langue
* civilité automatique :

  * FR → Mme / M.
  * EN → Ms / Mr
* contenu email personnalisé (texte fixe métier)
* CV adapté à la langue
* envoi via SMTP Gmail

---

### Rythme d’envoi

* envoi séquentiel
* pause aléatoire entre chaque email :

  * 45 à 90 secondes

---

### Affichage du suivi

Pendant l’envoi :

* affichage du numéro d’envoi global : `i / total`
* affichage de l’email en cours
* affichage du temps de pause avant prochain envoi

---

### Mise à jour Google Sheet

Après chaque envoi :

* `Envoyé : No → Yes`

---

## 10. Interface Streamlit

Fonctionnalités :

* upload du CV FR
* upload du CV EN
* affichage des leads
* masquage des leads
* lancement envoi automatique
* suivi en temps réel (progression + statut)

---

## 11. Sécurité anti-erreur

* suppression des doublons email
* protection contre re-soumission manuelle
* blocage des lignes incomplètes
* protection contre envoi multiple du même email

---

## 12. Arborescence du projet

```text
email-sender/
├── main.py
├── pyproject.toml
├── .env
├── credentials.json
└── README.md
```

---

## 13. Sécurité Git

```gitignore
.env
credentials.json
```

---

## 14. Dépannage

### Aucun email envoyé

* vérifier `Envoyé = No`
* vérifier que toutes les colonnes sont remplies

### Doublons persistants

* vérifier que `clean_duplicates()` est exécuté

### Erreur Google Sheets

* vérifier partage avec service account
* vérifier `GOOGLE_SHEETS_ID`

### Erreur Gmail SMTP

* utiliser un mot de passe d’application Gmail

---

## 15. Évolutions possibles

* file d’envoi persistante (queue)
* retry automatique des échecs
* logs d’erreurs dans Google Sheet
* dashboard CRM complet
* segmentation avancée des leads

```

---
```
