# Technical debt

Known limitations that were accepted on purpose, with the reason and what would remove them.

| ID | Debt | Reason | How to remove it |
|---|---|---|---|
| TD-01 | The cloud app sleeps after 15 minutes without visitors; the first request then takes about one minute (affects NFR-06 and NFR-10). | The project uses the free plan of Render, because hosting must be free. | Move to a paid plan or a host without sleep. |
| TD-02 | HSTS is not set for subdomains and the site is not on the browser preload list. | The app runs on a subdomain of the hosting provider, not on its own domain. | Register an own domain and enable both settings. |
| TD-03 | After every change, all recipes of the business are recalculated (one middleware call). | Simple and always consistent; a café has tens of recipes, which takes a few milliseconds. | Recalculate only recipes reachable from the changed ingredient, recipe or equipment. |
| TD-04 | Each user belongs to exactly one business (one-to-one membership instead of 1..* in the class diagram). | Small businesses do not share staff accounts; it keeps access control simple. | Change the membership to a foreign key and let the user choose the business after login. |
| TD-05 | Only the guest menu and the PDF are bilingual; the back office is English only. | Guests need their language most; staff screens in two languages would double the translation work in this project. | Mark the remaining back-office texts for translation and add them to the German catalogue. |
