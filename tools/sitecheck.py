"""Click through the app like a user, then crawl every internal link and check the layout
at phone and desktop width.

Manual check, not part of CI. Start the app on an empty database first, then run:
    pip install playwright && python -m playwright install chromium
    BASE_URL=http://127.0.0.1:8002 SERVER_LOG=server.log python tools/sitecheck.py screenshots/
It reports broken links, missing titles or descriptions and horizontal overflow at 360 px and 1280 px.
"""

import os
import re
import sys
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

BASE, OUT = os.environ.get("BASE_URL", "http://127.0.0.1:8002"), sys.argv[1]
problems = []
OVERFLOW_JS = "document.documentElement.scrollWidth - document.documentElement.clientWidth"


def submit(page):
    page.click("main button[type=submit]")
    page.wait_for_load_state()


def crawl(page, start, label):
    seen, queue, external = set(), [start], set()
    while queue:
        url = queue.pop()
        if url in seen:
            continue
        seen.add(url)
        response = page.goto(url)
        if response.status >= 400:
            problems.append(f"[{label}] {response.status} {url}")
            continue
        for href in page.eval_on_selector_all("a[href]", "els => els.map(e => e.getAttribute('href'))"):
            if href.startswith(("mailto:", "tel:", "#")) or href.endswith((".pdf", ".png", ".svg")):
                continue
            full = urljoin(page.url, href)
            if urlparse(full).netloc != urlparse(BASE).netloc:
                external.add(full)
            elif "/logout" not in full:
                queue.append(full.split("#")[0])
    return seen, external


def check_layout(page, urls, label):
    for width in (360, 1280):
        page.set_viewport_size({"width": width, "height": 800})
        for url in sorted(urls):
            page.goto(url)
            over = page.evaluate(OVERFLOW_JS)
            if over > 0:
                problems.append(f"[{label}] {over}px horizontal overflow at {width}px: {url}")
            if not page.title() or not page.locator("meta[name=description]").get_attribute("content"):
                problems.append(f"[{label}] missing title or description: {url}")


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get("CHROME_PATH"))
    guest = browser.new_page()
    pages_guest, ext1 = crawl(guest, f"{BASE}/", "guest")
    check_layout(guest, pages_guest, "guest")
    guest.set_viewport_size({"width": 360, "height": 800})
    guest.goto(f"{BASE}/")
    guest.screenshot(path=f"{OUT}/m-home.png", full_page=True)
    guest.goto(f"{BASE}/no-such-page/")
    guest.screenshot(path=f"{OUT}/m-404.png")

    owner = browser.new_page(viewport={"width": 1280, "height": 900})
    owner.goto(f"{BASE}/signup/")
    owner.fill("#id_business_name", "Café Linde")
    owner.fill("#id_email", "inhaberin@cafe-linde.de")
    owner.fill("#id_password1", "Kuchen-und-Kaffee-9")
    owner.fill("#id_password2", "Kuchen-und-Kaffee-9")
    submit(owner)
    # Locally the confirmation e-mail is printed to the server log (console e-mail backend).
    with open(os.environ["SERVER_LOG"], encoding="utf-8") as server_log:
        owner.goto(re.findall(r"http://\S+/activate/\S+/", server_log.read())[-1])
    owner.goto(f"{BASE}/app/ingredients/new/")
    owner.screenshot(path=f"{OUT}/d-ingredient-form-no-supplier.png", full_page=True)
    owner.goto(f"{BASE}/app/suppliers/new/")
    owner.fill("#id_name", "Feinkost Rossi GmbH")
    owner.fill("#id_contact_person", "Marco Rossi")
    owner.fill("#id_phone", "+49 30 1234 5678")
    owner.fill("#id_email", "bestellung@feinkost-rossi.example")
    submit(owner)
    for name, contains, may, checked in [
        ("Basilikum-Pesto", ["milk", "nuts"], ["peanuts"], True),
        ("Weizenmehl Type 550", ["gluten"], [], True),
        ("Hausgemachte Mayonnaise", ["eggs", "mustard"], [], False),
    ]:
        owner.goto(f"{BASE}/app/ingredients/new/")
        owner.fill("#id_name", name)
        for a in contains:
            owner.check(f"input[name=contains][value={a}]")
        for a in may:
            owner.check(f"input[name=may_contain][value={a}]")
        if checked:
            owner.check("#id_data_complete")
        submit(owner)
    owner.goto(f"{BASE}/app/")
    owner.click("text=Load example data")
    owner.wait_for_load_state()
    owner.screenshot(path=f"{OUT}/d-recipes.png", full_page=True)
    owner.click("text=Smoked salmon sandwich")
    owner.wait_for_load_state()
    owner.screenshot(path=f"{OUT}/d-recipe-detail.png", full_page=True)
    owner.goto(f"{BASE}/app/recipes/")
    owner.click("main >> text=Oat flat white")
    owner.wait_for_load_state()
    owner.screenshot(path=f"{OUT}/d-oat-flat-white.png", full_page=True)
    owner.goto(f"{BASE}/app/ingredients/")
    owner.click("text=Basil pesto >> xpath=ancestor::tr >> text=Edit")
    owner.wait_for_load_state()
    owner.uncheck("input[name=contains][value=nuts]")
    owner.click("main button[type=submit]")
    owner.wait_for_load_state()
    owner.screenshot(path=f"{OUT}/d-impact.png", full_page=True)
    owner.goto(f"{BASE}/app/approvals/")
    owner.screenshot(path=f"{OUT}/d-approvals.png", full_page=True)
    owner.goto(f"{BASE}/app/history/")
    owner.screenshot(path=f"{OUT}/d-history.png")
    owner.goto(f"{BASE}/app/staff/new/")
    owner.fill("#id_email", "koch@cafe-linde.de")
    owner.fill("#id_password1", "Topf-und-Deckel-7")
    owner.fill("#id_password2", "Topf-und-Deckel-7")
    submit(owner)
    owner.goto(f"{BASE}/app/")
    owner.screenshot(path=f"{OUT}/d-dashboard.png")
    owner.goto(f"{BASE}/app/ingredients/")
    owner.screenshot(path=f"{OUT}/d-ingredients.png")

    pages_owner, ext2 = crawl(owner, f"{BASE}/app/", "owner")
    check_layout(owner, pages_owner, "owner")

    owner.set_viewport_size({"width": 360, "height": 800})
    for path, name in [
        ("/app/recipes/", "m-recipes"),
        ("/app/ingredients/", "m-ingredients"),
        ("/app/suppliers/", "m-suppliers"),
        ("/app/ingredients/new/", "m-ingredient-form"),
    ]:
        owner.goto(BASE + path)
        owner.screenshot(path=f"{OUT}/{name}.png", full_page=True)
    owner.goto(f"{BASE}/app/")
    owner.click(".navbar-toggler")
    owner.wait_for_timeout(500)
    if not owner.locator("#mainnav a", has_text="Suppliers").is_visible():
        problems.append("mobile menu does not open")
    owner.screenshot(path=f"{OUT}/m-menu-open.png")
    browser.close()

print(f"guest pages: {len(pages_guest)}, owner pages: {len(pages_owner)}")
print("external links:", *sorted(ext1 | ext2), sep="\n  ")
print("PROBLEMS:" if problems else "No problems found.", *problems, sep="\n  ")
