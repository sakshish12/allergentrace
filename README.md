# AllergenTrace

Allergen and cross-contact transparency for small food businesses.

AllergenTrace lets cafés, bakeries and small restaurants enter allergens once per ingredient. The declaration of every dish is then calculated from its recipe, including sub-recipes and "may contain" warnings from shared equipment. Guests read the result in a bilingual QR menu, and the owner can print an allergen list as written documentation (Regulation (EU) No 1169/2011, LMIDV).

This repository is part of the IU portfolio "Project: Software Engineering" (DLMCSPSE01) by Sakshi Sharma.

## Try it online

The app runs at <https://allergentrace.onrender.com> (free hosting: after 15 minutes without visitors the first page takes up to a minute to load). Register your own business on the start page, or use the demo café whose login data is given in the portfolio submission. The step-by-step guide for owners, kitchen staff, service staff and guests is in the [installation and user manual](docs/installation-manual.pdf).

## Run it locally with Docker (recommended)

Requirements: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows, macOS) or Docker Engine with the Compose plugin (Linux).

```bash
git clone https://github.com/sakshish12/allergentrace.git
cd allergentrace
docker compose up --build
```

Open <http://localhost:8000>. The first start takes a few minutes because Docker downloads Python and PostgreSQL. Stop the app with `Ctrl+C`; `docker compose down -v` also deletes the local database.

For a ready-to-try café, set a password before the first start, for example `DJANGO_DEMO_PASSWORD=Demo-2026 docker compose up --build`. The start script then creates "Café Demo" with example data and three accounts, `demo-owner@example.com`, `demo-kitchen@example.com` and `demo-service@example.com`, all with that password. Without the variable you register your own business on the start page.

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
python manage.py createcachetable   # table for login rate limits
python manage.py runserver
```

All configuration variables are listed in [`.env.example`](.env.example).

The PDF allergen list uses WeasyPrint, which needs the Pango library of the operating system ([installation notes](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html)); the Docker image already contains it.

The guest menu is available in German and English. The German texts are in `locale/de/LC_MESSAGES/django.po`; after changing them, compile the file with `python manage.py compilemessages` (needs GNU gettext). The compiled `.mo` file is committed, so the app runs without gettext.

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
| Architecture diagrams (PlantUML sources and images) | [docs/architecture/](docs/architecture/) |
| User interface design and colours | [docs/design.md](docs/design.md) |
| Test report (automated and manual tests) | [docs/test-report.md](docs/test-report.md) |
| Usability test | [docs/usability-test.md](docs/usability-test.md) |
| Installation and user manual (PDF) | [docs/installation-manual.pdf](docs/installation-manual.pdf) |

The sprint plan is visible as [milestones](https://github.com/sakshish12/allergentrace/milestones) and the user stories as [issues](https://github.com/sakshish12/allergentrace/issues).

## Third-party software

Django, psycopg, dj-database-url, Gunicorn, WhiteNoise, django-simple-history, WeasyPrint, segno and bcrypt (see `requirements.txt`), Bootstrap 5.3 (MIT licence, bundled in `static/vendor/bootstrap`), and the fonts Atkinson Hyperlegible and Bricolage Grotesque (SIL Open Font Licence, bundled in `static/vendor/fonts`). E-mails in the cloud version are sent through the [Brevo](https://www.brevo.com/) transactional e-mail API.
