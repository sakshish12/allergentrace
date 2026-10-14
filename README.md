# AllergenTrace

Allergen and cross-contact transparency for small food businesses.

AllergenTrace lets cafés, bakeries and small restaurants enter allergens once per ingredient. The declaration of every dish is then calculated from its recipe, including sub-recipes and "may contain" warnings from shared equipment. Guests read the result in a bilingual QR menu, and the owner can print an allergen list as written documentation (Regulation (EU) No 1169/2011, LMIDV).

This repository is part of the IU portfolio "Project: Software Engineering" (DLMCSPSE01) by Sakshi Sharma.

## Run it locally with Docker (recommended)

Requirements: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows, macOS) or Docker Engine with the Compose plugin (Linux).

```bash
git clone https://github.com/sakshish12/allergentrace.git
cd allergentrace
docker compose up --build
```

Open <http://localhost:8000>. The first start takes a few minutes because Docker downloads Python and PostgreSQL. Stop the app with `Ctrl+C`; `docker compose down -v` also deletes the local database.

To check that the app and the database are running, open <http://localhost:8000/health/>. It should show `{"status": "ok", "database": "ok"}`.

## Run it without Docker (for development)

Requirements: Python 3.13 and a running PostgreSQL server (version 17 recommended).

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
export DJANGO_DEBUG=True           # Windows: set DJANGO_DEBUG=True
export DATABASE_URL=postgres://USER:PASSWORD@localhost:5432/allergentrace
python manage.py migrate
python manage.py runserver
```

All configuration variables are listed in [`.env.example`](.env.example).

## Tests and code quality

```bash
pytest                      # automated tests (needs DATABASE_URL, see above)
ruff check . && ruff format --check .
```

GitHub Actions runs the linter, Django's deployment checks, the tests against PostgreSQL 17 and a Docker Compose smoke test on every push.

## Documentation

| Topic | File |
|---|---|
| User stories (product backlog) | [docs/requirements/user-stories.md](docs/requirements/user-stories.md) |
| Business rules of the calculation | [docs/requirements/business-rules.md](docs/requirements/business-rules.md) |
| Non-functional requirements | [docs/requirements/non-functional-requirements.md](docs/requirements/non-functional-requirements.md) |
| Technical debt | [docs/technical-debt.md](docs/technical-debt.md) |

The sprint plan is visible as [milestones](https://github.com/sakshish12/allergentrace/milestones) and the user stories as [issues](https://github.com/sakshish12/allergentrace/issues).

## Third-party software

Django, psycopg, dj-database-url, Gunicorn and WhiteNoise (see `requirements.txt`), and Bootstrap 5.3 (MIT licence, bundled in `static/vendor/bootstrap`).
