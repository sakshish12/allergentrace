# Non-functional requirements

The non-functional requirements are structured along the product quality model of ISO/IEC 25010:2023. Each requirement names how it is verified. Requirements that cannot be met within the project are listed as technical debt in `docs/technical-debt.md`.

| ID | Quality characteristic | Requirement | Verification |
|---|---|---|---|
| NFR-01 | Functional suitability (correctness) | The allergen calculation follows BR-1 to BR-6 for every recipe graph. | Unit and property-based tests (pytest, Hypothesis); 100 % branch coverage of `allergen_engine`. |
| NFR-02 | Security (confidentiality, integrity) | A user can only read and change data of their own business, and only within the rights of their role. | Automated access-control tests for every view. |
| NFR-03 | Security | The application uses HTTPS in production, Django's CSRF and XSS protection, and stores passwords only as hashes. | `manage.py check --deploy` in CI; code review. |
| NFR-04 | Interaction capability (usability) | A first-time owner can create a dish with five ingredients in under five minutes without help. | Manual usability test with test users (TC-U1). |
| NFR-05 | Interaction capability (accessibility) | The guest menu meets WCAG 2.2 level AA for contrast, text size and keyboard use. | Manual test with a contrast checker and keyboard only. |
| NFR-06 | Performance efficiency | The guest menu of a business with 100 dishes is rendered in under one second server time, once the server is running. | Measurement in a test with seeded data. |
| NFR-07 | Compatibility | The application works in current versions of Chrome, Firefox and Safari and on screens from 360 px width. | Manual browser test; Playwright tests in Chromium. |
| NFR-08 | Maintainability (modularity, testability) | `allergen_engine` has no dependency on Django; code passes the Ruff linter without errors. | Import check in tests; Ruff in CI. |
| NFR-09 | Flexibility (installability) | The whole application starts with one command (`docker compose up`). | Fresh start on a clean machine following the README. |
| NFR-10 | Reliability (availability) | The public menu is reachable without login in at least 95 % of a calendar month. A first request after a pause may take up to 60 seconds while the free instance wakes up (TD-01); this counts as available. | Monthly check of the hosting provider's event log and status page. |
| NFR-11 | Data protection (GDPR) | All data is hosted in the EU; the guest menu stores no personal data and sets no tracking cookies. | Check of hosting regions and of cookies in the browser. |
