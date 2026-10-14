# Product backlog: user stories

This file is the single source of the functional requirements of AllergenTrace. Every story also exists as a GitHub issue with the same ID, so that progress can be followed on the project board. Priorities follow MoSCoW, effort is estimated in story points (1, 2, 3, 5, 8), and the sprint column shows the planned sprint. The business rules BR-1 to BR-6 are defined in `business-rules.md`.

Roles inherit rights: Owner ⊃ Kitchen ⊃ Service. Guests do not log in.

## Epic A: Accounts and roles

### US-01 Register a business
- **Priority:** Must | **Points:** 3 | **Sprint:** 1
- **Story:** As an owner, I want to register my business together with my owner account, so that I can manage the allergen data of my business in one place.
- **Acceptance criteria:**
  - A registration form asks for business name, owner e-mail and password; after submitting, the owner is logged in.
  - Login and logout work; a wrong password shows an error and does not reveal whether the e-mail exists.
  - All data created later belongs to exactly one business.

### US-02 Invite staff with a role
- **Priority:** Must | **Points:** 3 | **Sprint:** 1
- **Story:** As an owner, I want to create accounts for my staff with the role Kitchen or Service, so that everyone can only do the tasks that fit their job.
- **Acceptance criteria:**
  - The owner can create, deactivate and change the role of staff accounts.
  - Service staff can read dishes but cannot change any data.
  - Kitchen staff can edit ingredients, recipes and equipment, but cannot approve or publish.
  - A user of one business never sees or changes data of another business (tested automatically).

## Epic B: Ingredients, suppliers and equipment

### US-03 Record suppliers
- **Priority:** Must | **Points:** 2 | **Sprint:** 1
- **Story:** As kitchen staff, I want to record the suppliers we buy from, so that I can see where an ingredient comes from when its data changes.
- **Acceptance criteria:**
  - A supplier has a name and optional contact details.
  - An ingredient can be linked to one supplier.

### US-04 Record an ingredient with its allergens
- **Priority:** Must | **Points:** 5 | **Sprint:** 1
- **Story:** As kitchen staff, I want to enter an ingredient once with its status for each of the 14 allergens, so that I never have to enter allergens per dish again.
- **Acceptance criteria:**
  - The form shows all 14 allergens of Annex II of Regulation (EU) No 1169/2011.
  - Each allergen has one status: contains, may contain, free or unknown.
  - The default status of every allergen is "unknown", never "free" (BR-4).
  - An ingredient has a name, an optional product name and an optional supplier.

### US-05 Record equipment
- **Priority:** Must | **Points:** 2 | **Sprint:** 3
- **Story:** As kitchen staff, I want to record our equipment and mark whether it is dedicated to one dish, so that cross-contact from shared equipment can be detected.
- **Acceptance criteria:**
  - Equipment has a name and a flag "dedicated".
  - A recipe can be linked to several pieces of equipment.

## Epic C: Recipes and allergen calculation

### US-06 Build recipes from ingredients and sub-recipes
- **Priority:** Must | **Points:** 5 | **Sprint:** 2
- **Story:** As kitchen staff, I want to build a recipe from ingredients and other recipes (e.g. a sauce), so that a change to the sauce reaches every dish that uses it.
- **Acceptance criteria:**
  - A recipe has a name, a flag "dish" (shown on the menu) and a list of components.
  - A component is either an ingredient or another recipe.
  - An edit that would create a cycle (a recipe containing itself, directly or indirectly) is rejected with a clear message (BR-5).

### US-07 Calculate allergens automatically
- **Priority:** Must | **Points:** 8 | **Sprint:** 2
- **Story:** As an owner, I want the allergens of every dish to be calculated from its recipe, so that the declaration is always consistent with the ingredients.
- **Acceptance criteria:**
  - The declaration contains every allergen of every component at any depth (BR-1).
  - "Contains" overrides "may contain" for the same allergen (BR-2).
  - If any component has the status "unknown" for an allergen, the dish shows "please ask staff" for it and never "free" (BR-4).
  - The calculation is covered by unit tests and property-based tests.

### US-08 Explain why a dish contains an allergen
- **Priority:** Must | **Points:** 3 | **Sprint:** 2
- **Story:** As service staff, I want to see why a dish contains an allergen, so that I can answer a guest's question correctly.
- **Acceptance criteria:**
  - For each allergen of a dish, the path to its source is shown (e.g. "Pasta → Pesto → Cashews").
  - For "may contain" from equipment, the shared equipment and the other recipe are named.

### US-09 Derive cross-contact from shared equipment
- **Priority:** Must | **Points:** 5 | **Sprint:** 3
- **Story:** As an owner, I want "may contain" warnings to be derived from shared equipment, so that cross-contact is declared even if nobody writes it down.
- **Acceptance criteria:**
  - If two recipes use the same non-dedicated equipment, each receives the allergens contained in the other as "may contain" (BR-3).
  - Dedicated equipment never causes cross-contact.

## Epic D: Changes, approval and publication

### US-10 See the impact of a change
- **Priority:** Must | **Points:** 5 | **Sprint:** 3
- **Story:** As an owner, I want to see which dishes are affected after an ingredient or recipe changes, so that no declaration silently becomes wrong.
- **Acceptance criteria:**
  - After saving a change, a list shows every affected dish with allergens added and removed.
  - Dishes whose declaration does not change are not listed.

### US-11 Publish safely (fail-safe rule)
- **Priority:** Must | **Points:** 5 | **Sprint:** 3
- **Story:** As an owner, I want new allergens to be published at once and removed allergens only after my approval, so that guests are never told that a dish is safer than it really is.
- **Acceptance criteria:**
  - Added allergens appear in the published declaration immediately (BR-6).
  - Removed allergens stay published until the owner approves the removal.
  - Only the owner can approve; kitchen staff see "waiting for approval".

### US-12 Keep a change history
- **Priority:** Must | **Points:** 3 | **Sprint:** 3
- **Story:** As an owner, I want every change to ingredients, recipes and approvals to be stored with user and time, so that I can show food control what happened and when.
- **Acceptance criteria:**
  - The history shows date, user and changed fields for ingredients, recipes and declarations.
  - History entries cannot be edited in the user interface.

## Epic E: Guest menu and documentation

### US-13 Choose the dishes on the menu
- **Priority:** Must | **Points:** 2 | **Sprint:** 4
- **Story:** As an owner, I want to choose which dishes appear on the public menu, so that guests only see what we currently serve.
- **Acceptance criteria:**
  - Each dish can be switched on or off for the menu.
  - Only published declarations are shown to guests, never unapproved data.

### US-14 Read the menu on my own phone
- **Priority:** Must | **Points:** 5 | **Sprint:** 4
- **Story:** As a guest with a food allergy, I want to open the menu on my phone in German or English, so that I can check the allergens before I order.
- **Acceptance criteria:**
  - The menu opens without login under a public link of the business.
  - The language can be switched between German and English.
  - The page is usable on a 360 px wide screen and meets WCAG 2.2 level AA for contrast and keyboard use.

### US-15 Hide dishes with my allergens
- **Priority:** Must | **Points:** 3 | **Sprint:** 4
- **Story:** As a guest, I want to select my allergens and hide all dishes that contain them, so that I quickly see what I can eat.
- **Acceptance criteria:**
  - Selecting allergens hides dishes that contain them; "may contain" is hidden by default and can be shown.
  - Dishes with "please ask staff" for a selected allergen stay visible with a clear warning.

### US-16 Print the allergen list
- **Priority:** Must | **Points:** 3 | **Sprint:** 4
- **Story:** As an owner, I want to download a PDF allergen list of all dishes on the menu, so that I have the written documentation that the LMIDV requires.
- **Acceptance criteria:**
  - The PDF lists every menu dish with its 14 allergens and the date of creation.
  - The PDF uses the published declarations only.

### US-17 Print a QR code for the tables
- **Priority:** Must | **Points:** 2 | **Sprint:** 4
- **Story:** As an owner, I want to download a QR code that links to my menu, so that I can put it on tables and the counter.
- **Acceptance criteria:**
  - The QR code opens the public menu of the business.
  - It can be downloaded as PNG and SVG.

## Should and Could stories

### US-18 List ingredients with unknown data
- **Priority:** Should | **Points:** 2 | **Sprint:** 5
- **Story:** As kitchen staff, I want a list of all ingredients with "unknown" allergen data, so that I know which suppliers I still have to ask.
- **Acceptance criteria:**
  - The list shows each ingredient with its unknown allergens and its supplier.

### US-19 Copy a recipe
- **Priority:** Should | **Points:** 2 | **Sprint:** 5
- **Story:** As kitchen staff, I want to copy an existing recipe, so that I can create a variant (e.g. a vegan version) quickly.
- **Acceptance criteria:**
  - The copy has the same components and equipment and a new name.

### US-20 E-mail when approval is needed
- **Priority:** Should | **Points:** 3 | **Sprint:** 5
- **Story:** As an owner, I want to receive an e-mail when an allergen removal waits for my approval, so that the menu does not stay outdated for long.
- **Acceptance criteria:**
  - One e-mail is sent per change that needs approval, with a link to the approval page.

### US-21 Import product data by barcode
- **Priority:** Could | **Points:** 5 | **Sprint:** –
- **Story:** As kitchen staff, I want to fill in an ingredient from its barcode using Open Food Facts, so that I type less.
- **Acceptance criteria:**
  - Imported allergens are only a suggestion and must be confirmed by a person.

### US-22 Import ingredients from a CSV file
- **Priority:** Could | **Points:** 3 | **Sprint:** –
- **Story:** As an owner, I want to import my existing allergen spreadsheet, so that I do not start from zero.
- **Acceptance criteria:**
  - Rows with errors are reported and not imported.

## Out of scope (Won't have in this project)

Nutrition values, food costing, ordering and stock management, and multi-site chains.
