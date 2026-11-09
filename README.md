# LaurentConvert

Application web d'extraction de texte et de tableaux depuis des images, avec
vérification qualité et validation humaine.

- **Backend** : Django 5 + Django REST Framework + SimpleJWT
- **Frontend** : React 18 + Vite + TailwindCSS (interface en français)
- **Extraction** : API Groq (modèle vision multimodal, ex. `qwen/qwen3.8-27b`) via une couche de service interchangeable
- **Base** : SQLite en développement, MariaDB en production

## Structure

```
backend/    Projet Django (apps : accounts, clients, conversions)
frontend/   Application React/Vite
.env        Configuration locale (à créer depuis .env.example, jamais commité)
```

## Installation (développement)

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows : .venv\Scripts\activate   |   Linux/macOS : source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env        # puis éditer ../.env
python manage.py migrate
python manage.py createsuperuser  # crée le premier administrateur
python manage.py runserver        # http://localhost:8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173 (proxy /api → :8000)
```

Ouvrir http://localhost:5173 et se connecter avec le superutilisateur.
Le compte créé via `createsuperuser` obtient automatiquement le rôle
« administrateur ».

## Variables d'environnement (.env)

| Variable | Rôle |
|---|---|
| `DJANGO_SECRET_KEY` | Clé secrète Django (obligatoire hors debug) |
| `DJANGO_DEBUG` | `true`/`false` |
| `DJANGO_ALLOWED_HOSTS` | Hôtes autorisés, séparés par des virgules |
| `MYSQL_NAME`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_PORT` | MariaDB ; laisser `MYSQL_NAME` vide → SQLite |
| `GROQ_API_KEY` | Clé API Groq (obligatoire pour les conversions) |
| `GROQ_MODEL` | Modèle vision (défaut : `qwen/qwen3.8-27b`) |
| `GROQ_API_URL`, `GROQ_TIMEOUT_SECONDS` | Endpoint et timeout |
| `CORS_ALLOWED_ORIGINS` | Origines frontend autorisées |
| `MAX_UPLOAD_SIZE_MB`, `ALLOWED_IMAGE_TYPES`, `MEDIA_ROOT` | Limites d'upload |
| `JWT_ACCESS_MINUTES`, `JWT_REFRESH_DAYS` | Durées des jetons |

Si `GROQ_API_KEY` est absente, toute tentative de conversion échoue avec un
message explicite (la conversion est marquée « Échouée » et peut être relancée).

## Production (MariaDB)

1. Créer la base : `CREATE DATABASE laurentconvert CHARACTER SET utf8mb4;`
2. Installer le pilote : `pip install mysqlclient` (ou `pymysql` + `pymysql.install_as_MySQLdb()`).
3. Renseigner `MYSQL_*` dans `.env`, `DJANGO_DEBUG=false`, `DJANGO_SECRET_KEY`,
   `DJANGO_ALLOWED_HOSTS` et `CORS_ALLOWED_ORIGINS` (domaine réel).
4. `python manage.py migrate && python manage.py collectstatic`
5. Servir via un WSGI/ASGI (gunicorn, uvicorn…) derrière un reverse proxy
   qui sert aussi `/media/` avec contrôle d'accès.

## API principale

| Méthode | Endpoint | Rôle |
|---|---|---|
| POST | `/api/auth/token/` | Connexion (JWT + profil) |
| POST | `/api/auth/token/refresh/` | Rafraîchir le jeton |
| GET/PATCH | `/api/auth/me/` | Profil courant |
| POST | `/api/auth/change-password/` | Changer son mot de passe |
| CRUD | `/api/users/` | Comptes (admin uniquement ; DELETE = désactivation) |
| CRUD | `/api/clients/` | Clients (+ `archive/`, `restore/`, `images/`, `conversions/`, `?search=`) |
| CRUD | `/api/images/` | Upload multipart `file` (+`client`), filtres `?client=`, `?status=` |
| POST | `/api/images/{id}/convert/` | Lancer une conversion `{type: "text"|"table"}` |
| GET | `/api/conversions/` | Liste (`?status=`, `?type=`, `?client=`, `?image=`) |
| PATCH | `/api/conversions/{id}/text/` | Corriger le texte extrait |
| PATCH | `/api/conversions/{id}/table/` | Corriger le tableau (`corrected_data`) |
| POST | `/api/conversions/{id}/decide/` | Valider / rejeter `{decision, comment}` |
| POST | `/api/conversions/{id}/retry/` | Relancer une conversion échouée |
| GET | `/api/conversions/{id}/export_csv/` | Export CSV (UTF-8 avec BOM) |
| GET | `/api/conversions/{id}/export_xlsx/` | Export Excel .xlsx (openpyxl) |

## Traitement Groq : prérequis et limites

- Les conversions sont envoyées à un **modèle vision** Groq via l'API Chat
  Completions (image encodée en base64). Les modèles accessibles dépendent
  du compte : `GET https://api.groq.com/openai/v1/models` avec votre clé
  pour vérifier la disponibilité de `GROQ_MODEL` (les modèles vision
  évoluent ; `qwen/qwen3.8-27b` est multimodal : max 3 images/requête,
  20 Mo/image).
- Le traitement est **synchrone** (la requête attend la réponse de Groq). Pour
  de gros volumes, prévoir une file de tâches (Celery) — la couche
  `conversions/services.py` est conçue pour être interchangeables.
- Groq ne fournit **pas de score de confiance OCR** : l'indicateur affiché est
  une heuristique locale (résultat vide, caractères illisibles, lignes
  incohérentes…). Il signale les cas suspects, il ne garantit pas l'exactitude.
  La validation humaine (image ↔ résultat) reste l'étape décisive.

## Qualité et sécurité

- Upload : taille limitée, type MIME **vérifié côté serveur** (signature Pillow,
  le type déclaré par le navigateur n'est pas utilisé).
- JWT court + refresh ; routes admin protégées par le rôle applicatif.
- Résultat brut **et** corrections conservés ; chaque décision de validation
  enregistre l'auteur, la date et un commentaire.
- Aucune clé dans le code : tout passe par `.env`.

## Tests

```bash
cd backend
python manage.py test        # 21 tests : auth, permissions, upload, OCR mocké, qualité
```

Frontend : `npm run build` pour vérifier la compilation.
