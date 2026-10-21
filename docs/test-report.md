# Test report (final version)

This report covers the automated tests, the manual test cases TC-01 to TC-12 from the test plan, an exploratory test of the whole site and the usability test. All tests were run against the final version of the code.

## 1. Automated tests

The suite has 139 tests and runs on every push in GitHub Actions against PostgreSQL 17, together with the linter (Ruff), Django's deployment checks, a check for missing migrations and a Docker Compose smoke test.

| Test suite | What it checks | Tests |
|---|---|---|
| `tests/engine/test_properties.py` | Property-based tests (Hypothesis): the business rules hold for any acyclic recipe graph | 7 |
| `tests/engine/test_rules.py` | One or more examples per business rule BR-1 to BR-6 | 10 |
| `tests/engine/test_sprint3_rules.py` | Cross-contact, impact of a change, fail-safe publication | 8 |
| `tests/engine/test_sprint4_rules.py` | Which dishes the guest filter hides | 6 |
| `tests/test_engine_model.py` | The 14 Annex II allergens with both labels; the engine does not depend on Django | 2 |
| `tests/test_accounts.py` | Registration with e-mail confirmation, staff accounts and roles, demo café | 13 |
| `tests/test_security.py` | Rate limit, login delay and lockout, bcrypt hashing, password reset, input cleaning | 10 |
| `tests/test_catalog.py` | Suppliers and ingredients, roles and separation of businesses | 9 |
| `tests/test_recipes.py` | Recipes, sub-recipes, calculation and explanation through the web app | 13 |
| `tests/test_sprint3.py` | Equipment, cross-contact, impact, approval, change history | 9 |
| `tests/test_sprint4.py` | Menu selection, public guest menu, filter, PDF list, QR code | 12 |
| `tests/test_sprint5.py` | Unknown-data list, copying a recipe, e-mail when an approval is needed | 8 |
| `tests/test_pages.py` | Titles, descriptions, error pages, messages, privacy and terms pages | 14 |
| `tests/test_example_data.py` | The example café is consistent, shows the rules and never changes own entries | 5 |
| `tests/test_smoke.py` | The app starts, reaches the database, apps only depend downwards | 4 |
| `tests/test_user_findings.py` | Problems found in the exploratory test (section 3) | 9 |

The allergen engine has 100 % line and branch coverage; CI fails if this drops.

## 2. Manual test cases

The test cases were executed in Chrome against a local installation of the final version with the example café. TC-U1 is reported in [usability-test.md](usability-test.md).

| ID | Covers | Result | Observation |
|---|---|---|---|
| TC-01 | US-01 | Pass | Since the security work, registration sends a confirmation e-mail; after opening the link the owner is logged in. A wrong password and an unknown e-mail give the same message ("Incorrect email or password"). |
| TC-02 | US-02, NFR-02 | Pass | Service staff see the ingredient list without Edit or Delete; opening an edit URL directly shows the 403 page. |
| TC-03 | US-04, BR-4 | Pass | A new ingredient without the "checked" tick is "Unknown"; the dish using it shows "Please ask staff". |
| TC-04 | US-06, BR-1 | Pass | A dish with the sub-recipe Herb mayo declares eggs, mustard and sulphites, with the path through Herb mayo. |
| TC-05 | US-06, BR-5 | Pass | Adding a dish to its own sub-recipe is rejected with an explanation; nothing is saved. |
| TC-06 | US-09, BR-3 | Pass | Oat flat white shows "may contain milk" with the steam wand and Cappuccino as the source. |
| TC-07 | US-10, US-11, BR-6 | Pass | Kitchen staff remove Feta from Avocado toast; the impact message names milk; the guest menu keeps milk until the owner approves, then drops it. |
| TC-08 | US-12 | Pass | The history lists the change with date and user, without an edit option. During this test the history showed a user number instead of the e-mail for "approved by"; this was fixed (section 3). |
| TC-09 | US-13, US-14 | Pass | The guest menu opens without login on a 360 px wide phone screen; an unticked dish is missing; texts and allergen names switch between German and English. |
| TC-10 | US-15 | Pass | Selecting milk hides dishes with milk and with traces of milk; traces are shown again with the tick; selecting fish also hides the salmon sandwich; dishes with unchecked data stay visible with a warning. |
| TC-11 | NFR-05, NFR-07 | Partly | In Chrome at 360 px every control is reachable with the keyboard, the focus is always visible and nothing scrolls sideways. Colour contrast is documented in [design.md](design.md). Firefox and Safari were not tested. |
| TC-12 | US-16, US-17 | Pass | The PDF lists every menu dish with the 14 allergen columns and the creation date; the QR code downloads as PNG and SVG and opens the menu. |

## 3. Exploratory test

The whole site was also used the way a careless first-time user would: odd inputs, deleting things that are still in use, typing addresses by hand, double clicks, the wrong role, phone screens and very long names. The following problems were found and fixed; each fix has a test in `tests/test_user_findings.py` or was checked in the browser.

| Problem | Fix |
|---|---|
| A dish without any ingredients was shown to guests as free of all 14 allergens. | A recipe without parts counts as unknown data (BR-4) and shows "Please ask staff"; it is published once it has parts. |
| The same name could be used twice (also with different capital letters), which made the ingredient picker ambiguous. | Names of ingredients, recipes, suppliers and equipment are unique within a business. |
| A quantity written with a decimal comma (0,5) was rejected. | Both 0,5 and 0.5 are accepted. |
| A double click on "Save" created the entry twice. | A form is sent only once. |
| The history showed numbers instead of names for linked entries (for example the approving user). | Linked entries are shown by name. |
| After logging out, the message "You are logged out" was hidden behind the start page. | The message is shown above the page. |
| A long business name squeezed the "Log out" button. | The name is shortened in the menu bar. |
| Typing /logout/ in the address bar showed an error page. | A page asks for confirmation. |
| The login page was shown to users who were already logged in. | They are sent to the app. |
| A supplier phone number could contain letters. | Only digits and + ( ) / - are allowed. |
| Deleting a supplier or equipment that is still in use gave no warning. | The confirmation page names the affected ingredients or recipes. |

Checked without findings: other businesses' data cannot be opened, roles are enforced on every action, ingredients and recipes that are still used cannot be deleted, a recipe cannot contain itself, HTML in names is shown as text, unusual guest menu addresses do not cause errors, and the browser's Back button after logging out does not show app pages.

## 4. Usability test

A pilot with one participant; see [usability-test.md](usability-test.md). NFR-04 was met (3 min 41 s for a dish with five ingredients).
