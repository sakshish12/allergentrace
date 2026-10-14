# Technical debt

Known limitations that were accepted on purpose, with the reason and what would remove them.

| ID | Debt | Reason | How to remove it |
|---|---|---|---|
| TD-01 | The cloud app sleeps after 15 minutes without visitors; the first request then takes about one minute (affects NFR-06 and NFR-10). | The project uses the free plan of Render, because hosting must be free. | Move to a paid plan or a host without sleep. |
| TD-02 | HSTS is not set for subdomains and the site is not on the browser preload list. | The app runs on a subdomain of the hosting provider, not on its own domain. | Register an own domain and enable both settings. |
