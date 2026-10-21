# AllergenTrace – installation and user manual

AllergenTrace is a web application for cafés, bakeries and small restaurants. Allergens are entered once per ingredient; the app calculates the declaration of every dish from its recipe, including sauces and doughs used inside dishes and "may contain" warnings from shared equipment. Guests read the result in a QR menu on their own phone.

This manual explains three ways to run the application and then how to use it in each role.

| Way | Best for | What you need |
|---|---|---|
| A. Cloud version | Trying the app straight away | A web browser |
| B. Docker Compose | Running your own copy on a laptop | Docker Desktop (Windows, macOS) or Docker Engine (Linux) |
| C. Without Docker | Development | Python 3.13 and PostgreSQL 17 |

## A. Use the cloud version

1. Open <https://allergentrace.onrender.com>.
2. The app runs on a free plan that sleeps after 15 minutes without visitors. The first page can then take up to one minute to load; after that, pages open normally.
3. Either log in to the demo café (the login data is given in the portfolio submission), or click **Register your business** and create your own business. A confirmation link is sent to the e-mail address you enter.

The demo café has three accounts with the same password, one per role: `demo-owner@example.com`, `demo-kitchen@example.com` and `demo-service@example.com`. These addresses cannot receive e-mails, so "Forgot your password?" does not work for them. After five wrong passwords an account is paused for 15 minutes; the other two accounts can still be used.

## B. Install with Docker Compose

**Step 1.** Install Docker Desktop from <https://www.docker.com/products/docker-desktop/> (Windows, macOS) or Docker Engine with the Compose plugin (Linux), and start it.

**Step 2.** Get the code, either with Git or by downloading the ZIP file from GitHub and unpacking it:

```bash
git clone https://github.com/sakshish12/allergentrace.git
cd allergentrace
```

**Step 3.** Start the app and its database:

```bash
docker compose up --build
```

The first start takes a few minutes, because Docker downloads Python and PostgreSQL. The app is ready when the terminal shows `Listening at: http://0.0.0.0:8000`.

**Step 4.** Open <http://localhost:8000>. To check that the app and the database work, open <http://localhost:8000/health/>; it shows `{"status": "ok", "database": "ok"}`.

**Step 5.** Register a business. Locally no e-mails are sent: the confirmation e-mail, including its link, is printed in the terminal where Docker runs. Copy the link into the browser to activate the account.

**Optional: start with the demo café.** Set a password before starting, and the start script creates "Café Demo" with example data and the three demo accounts:

```bash
DJANGO_DEMO_PASSWORD=Demo-2026 docker compose up --build              # macOS, Linux
$env:DJANGO_DEMO_PASSWORD="Demo-2026"; docker compose up --build      # Windows PowerShell
```

**Stop and reset.** Press `Ctrl+C` to stop. `docker compose down` removes the containers but keeps the data; `docker compose down -v` also deletes the local database.

## C. Install without Docker

**Step 1.** Install Python 3.13 and PostgreSQL 17, and create an empty database, for example `allergentrace`.

**Step 2.** The PDF allergen list uses WeasyPrint, which needs the Pango library of the operating system; see <https://doc.courtbouillon.org/weasyprint/stable/first_steps.html>.

**Step 3.** In the project folder:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
export DJANGO_DEBUG=True           # Windows: set DJANGO_DEBUG=True
export DATABASE_URL=postgres://USER:PASSWORD@localhost:5432/allergentrace
python manage.py migrate
python manage.py createcachetable
python manage.py runserver
```

**Step 4.** Open <http://localhost:8000>. Confirmation e-mails are printed in the terminal, as with Docker.

### Configuration

All settings are environment variables; `.env.example` lists them.

| Variable | Meaning |
|---|---|
| `DATABASE_URL` | Connection to PostgreSQL |
| `DJANGO_SECRET_KEY` | Long random string; required when `DJANGO_DEBUG` is not `True` |
| `DJANGO_DEBUG` | `True` only for local development |
| `DJANGO_ALLOWED_HOSTS` | Host names the app answers to, separated by commas |
| `BREVO_API_KEY`, `DJANGO_DEFAULT_FROM_EMAIL` | Sending e-mails through Brevo; without a key, e-mails are printed to the log |
| `DJANGO_CONTACT_EMAIL` | Contact address in the privacy policy and terms of use |
| `DJANGO_DEMO_PASSWORD` | Creates the demo café at start-up; empty means no demo café |

### Tests

```bash
pytest                                   # automated tests (needs DATABASE_URL)
ruff check . && ruff format --check .    # code style
```

## User guide

The app knows three roles. Each role includes the rights of the one below it.

| Role | Can do |
|---|---|
| Owner | Everything, plus staff accounts, menu, approving allergen removals |
| Kitchen | Enter and change suppliers, ingredients, equipment and recipes |
| Service | Read everything, to answer guests' questions |

### Owner: getting started

1. **Register** the business on the start page and open the confirmation link from the e-mail.
2. On the **Overview** page, click **Load example data** to see a small café with ten recipes, or start with your own data. Example entries never change entries you already have.
3. Under **Staff**, create accounts for kitchen and service staff. Accounts are deactivated instead of deleted, so the change history keeps showing who changed what.

![Overview page](images/overview.png)

### Kitchen: ingredients and recipes

1. **Suppliers**: record whom you buy from, so you know whom to call about missing allergen data.
2. **Ingredients**: enter each ingredient once and tick its allergens from the product label, as "Contains" or "May contain (traces)". Tick **"I have checked these allergens…"** only after comparing with the label; otherwise the ingredient stays **Unknown**, and every dish using it shows "Please ask staff". **Ingredients → Unknown data** lists them with the supplier to contact.
3. **Equipment**: record shared equipment such as a toaster or fryer. Tick "dedicated to one recipe" only if it is never used for anything else.
4. **Recipes**: create a recipe, tick "Served as a dish" for dishes on the menu (untick it for sauces and doughs), and add its parts under **Add a part**. A sauce or dough can be its own recipe and be used inside dishes. Under **Equipment**, tick what the recipe is prepared with.
5. The **Allergen declaration** on the recipe page is calculated automatically and explains every allergen, for example "Milk: Pesto → Parmesan". Allergens that can pass between recipes through shared equipment appear as "May contain". **Copy** creates a variant of a recipe.

![Recipe page with the calculated declaration](images/recipe.png)

### Owner: approving removals

When a change would remove an allergen from a dish, guests keep seeing the old, safer declaration until the owner approves it. New allergens are shown to guests at once. The owner receives an e-mail when something waits for approval; **Approvals** lists the changes, and **History** shows every change with time and person.

### Owner: menu, QR code and allergen list

1. **Menu**: untick dishes that are not served at the moment and click **Save menu**.
2. Download the **QR code** (PNG or SVG) and print it on table cards. It opens the guest menu without a login.
3. **Download allergen list (PDF)** gives the written allergen information (14 allergens per dish) for the counter and for food control.

### Guests: the QR menu

1. Scan the QR code with the phone camera; the menu opens in the phone's language (German or English) and can be switched at the top.
2. Tap **Hide dishes with my allergens**, tick what you cannot eat and tap **Show dishes**. Dishes that may contain traces are hidden as well, unless you tick "Also show dishes that may contain traces".
3. A dish with **"Please ask our staff"** uses an ingredient whose allergen data has not been checked; ask before ordering.

![Guest menu on a phone](images/guest-menu.png)

## Troubleshooting

| Problem | Solution |
|---|---|
| The cloud version takes a minute to open | The free server is waking up; wait, then it is fast. |
| "Too many requests. Please wait a minute" | More than 10 login or registration attempts per minute came from your network; wait one minute. |
| Signing in is paused | After five wrong passwords the account is paused for 15 minutes; use "Forgot your password?" to set a new one. |
| No confirmation e-mail when running locally | Locally, e-mails are printed in the terminal instead of being sent. |
| Port 8000 is already in use | Stop the other program, or change `"8000:8000"` to `"8080:8000"` in `docker-compose.yml` and open <http://localhost:8080>. |
| "Please ask staff" on a dish | One of its ingredients is "Unknown", or the recipe has no parts yet. See **Ingredients → Unknown data**. |
