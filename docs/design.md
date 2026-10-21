# User interface design

## Direction

AllergenTrace is used by café and bakery staff during a working day and read by guests with allergies on their phones. The interface therefore aims to be calm, warm and easy to read rather than decorative. Its vocabulary comes from the kitchen: allergens appear as small labels (chips), and the start page shows a dish as a kitchen ticket that explains where each allergen comes from.

## Colours

The interface uses the AllergenTrace website colour palette. All text and control colours meet WCAG 2.2 level AA (checked with the WCAG contrast formula).

| Token | Hex | Use | Contrast |
|---|---|---|---|
| Mist | `#F0F4EF` | page background | – |
| Navy | `#0D1821` | body text, footer background | 16.2 : 1 on mist |
| Slate | `#344966` | buttons, links, focus ring, logo | 9.2 : 1 with white text |
| Light blue | `#B4CDED` | information messages, active menu item, footer links | 11.0 : 1 on navy |
| Sage | `#BFCC94` | "Checked" badges, success messages, tick in the logo | 10.5 : 1 with navy text |
| Muted (derived) | `#4A5A70` | secondary text | 6.3 : 1 on mist |
| Control line (derived) | `#7A8796` | borders of inputs and checkboxes | 3.7 : 1 (non-text, min. 3 : 1) |

Two signal colours stay outside the brand palette on purpose, because they carry safety meaning and must never look like decoration:

| Token | Hex | Use | Contrast |
|---|---|---|---|
| Amber | `#E8B04A` | "Unknown" data and "Please ask staff" | 9.2 : 1 with navy text |
| Red | `#A63A2B` | delete actions and errors | 6.4 : 1 with white text |

Status is never shown by colour alone: every badge also carries a word ("Checked", "Unknown").

## Typography

- **Atkinson Hyperlegible** (body text) was designed by the Braille Institute for readers with low vision; its letters are hard to confuse, which suits a product about safety information.
- **Bricolage Grotesque** (headings) adds warmth and character.

Both fonts are served from the application itself, not from Google Fonts, so no guest IP address is sent to a third party (NFR-11). Licence: SIL Open Font License (files in `static/vendor/fonts`).

## Layout rules

- Tables turn into stacked cards below 768 px, so no page scrolls sideways on a phone; the allergen entry table stays a table because its three columns fit.
- Every page has its own `<title>` and meta description; the logo links to the start page.
- Phone numbers and e-mail addresses are `tel:` and `mailto:` links.
- Success, info and error messages appear at the top of the page; form errors are summarised above the form and shown next to each field.
- Custom pages exist for 403 (role not allowed), 404 (not found) and 500 (server error).

## Surfaces and details

- Two radii only: 6 px for buttons and inputs, 8 px for tables, panels and messages; chips and status badges use 4 px.
- Surfaces are separated by a thin border or a tone step, never by a drop shadow. The kitchen ticket keeps its dark top strip and slight tilt but has no shadow and does not move on hover.
- Table headers are small, regular and grey on the white table, without a coloured band. Numbers and dates use tabular figures so columns line up.
- Red is kept for real warnings and the delete confirmation. Delete and remove links in lists are grey and turn red only on hover or keyboard focus.
- The dashboard shows the four counts (recipes, ingredients, suppliers, equipment) in one divided strip; each count links to its list.
- No small uppercase labels above headings. On the guest menu the business name is the heading and "Menu with allergens" sits below it.
- Buttons shrink slightly (to 97 %) while pressed, over 160 ms. Nothing else animates, and the press effect is switched off when the device asks for reduced motion.
- Text selection, checkbox colour and the text cursor use the brand colours.
- The start page shows a real piece of the guest menu (the same markup and styles) instead of an illustration.

## Checks

`tests/test_pages.py` covers titles, descriptions, error pages, messages and contact links. A browser walkthrough with Playwright and Chrome crawls all internal links and measures horizontal overflow at 360 px and 1280 px width.
