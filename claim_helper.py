#!/usr/bin/env python3
"""Local, supervised clothing-item entry. Never submits a claim."""
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from tempfile import TemporaryDirectory
import sys
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

ITEMS = [
    ("Men's Short Sleeve Striped Johnny Collar Sweater", "", "30.00"),
    ("Men's 7-inch Elevated Linen Shorts", "Goodfellow & Co.", "30.00"),
    ("Men's Short Sleeve Blanket Stitch Button-Down Shirt", "", "30.00"),
    ("Men's 7-inch Whip Stitch Pull-On Shorts", "Goodfellow & Co.", "30.00"),
    ("Women's Strapless Tube Tiered Mini Dress", "Wild Fable", "35.00"),
]
ROOT = Path(__file__).resolve().parent
JOURNAL = ROOT / "saved_items.json"

def visible_one(loc):
    matches = [loc.nth(i) for i in range(loc.count()) if loc.nth(i).is_visible()]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one visible control; found {len(matches)}.")
    return matches[0]

def field(page, pattern):
    return visible_one(page.get_by_label(re.compile(pattern, re.I)))

def choose(page, pattern, target):
    from screenshot_ai import dropdown_choice
    control = field(page, pattern)
    if control.evaluate("e => e.tagName") == "SELECT":
        options = control.locator("option").evaluate_all(
            "es => es.filter(e => !e.disabled && e.value && !/choose|select/i.test(e.textContent)).map(e => ({label:e.textContent.trim(),value:e.value}))")
        if not options:
            raise RuntimeError("No dropdown choices available.")
        n = dropdown_choice([o["label"] for o in options], target)
        control.select_option(value=options[n]["value"])
    else:
        control.click()
        options = page.get_by_role("option")
        labels = [options.nth(i).inner_text() for i in range(options.count()) if options.nth(i).is_visible()]
        if not labels:
            raise RuntimeError("Custom dropdown is not accessible. No item was saved.")
        n = dropdown_choice(labels, target)
        visible_one(page.get_by_role("option", name=labels[n], exact=True)).click()

def journal(saved):
    temporary = JOURNAL.with_suffix(".tmp")
    temporary.write_text(json.dumps(saved, indent=2))
    temporary.replace(JOURNAL)

def wait_for_item_form(context):
    """Keep the browser open across login redirects and popup tabs."""
    while True:
        input("Press Enter after login, when a blank Item Information form is open: ")
        ready = []
        for tab in context.pages:
            if tab.is_closed() or urlparse(tab.url).hostname != "claims-center.americanexpress.com":
                continue
            try:
                control = field(tab, r"^item name")
                if not control.input_value().strip():
                    ready.append(tab)
            except Exception:
                continue
        if len(ready) == 1:
            ready[0].bring_to_front()
            return ready[0]
        if len(ready) > 1:
            print("More than one blank claim form is open. Close the extra blank form tabs and try again.")
        else:
            print("The blank item form is not ready yet. The browser will stay open.")
            print("Finish login/2FA, open your existing claim, then open a blank clothing item at Item Information.")
            print("If Amex itself shows an error, share that error or a screenshot without credentials.")

def run():
    from playwright.sync_api import sync_playwright
    from screenshot_reader import selected_files, dropzone, review
    from screenshot_ai import extract, client
    client()
    saved = json.loads(JOURNAL.read_text()) if JOURNAL.exists() else []
    with TemporaryDirectory(prefix="amex-receipts-") as receipt_dir, sync_playwright() as pw:
        # Temporary browser profile; no credentials or browser cookies are saved by this script.
        browser = pw.chromium.launch(channel="chrome", headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(10000)
        files = selected_files() if len(sys.argv) > 1 else dropzone(page, receipt_dir)
        rows = extract(files, ITEMS)
        items = review(page, rows, {})
        page.goto("https://claims-center.americanexpress.com/home")
        print("\nLog in yourself, complete 2FA, and navigate to Item Information.")
        print("Keep existing headphones saved. Open a NEW blank clothing item form.")
        page = wait_for_item_form(context)
        for item in items:
            key = [item['name'], item['date'], item['cost']]
            if key in saved:
                print(f"Skipping previously saved item: {item['name']}")
                continue
            if urlparse(page.url).hostname != "claims-center.americanexpress.com":
                raise RuntimeError("The browser is no longer on the Amex claims site.")
            print(f"\nEntering: {item['name']}")
            # Require a blank new form; never overwrite an existing item.
            try:
                name_control = field(page, r"^item name")
                if name_control.input_value().strip():
                    raise RuntimeError("Item form contains data. Open a new blank item.")
            except Exception:
                pattern = re.compile(r"^add (?:another |new |an? )?item$", re.I)
                add = page.get_by_role("button", name=pattern).or_(page.get_by_role("link", name=pattern))
                visible_one(add).click()
                name_control = field(page, r"^item name")
                if name_control.input_value().strip():
                    raise RuntimeError("Refusing to overwrite an existing item.")
            name_control.fill(item['name'])
            field(page, r"^purchase date of item").fill(item['date'])
            choose(page, r"^item type", "Clothing / Apparel")
            choose(page, r"^item description", item["name"])
            field(page, r"^merchant").fill("Target")
            field(page, r"^manufacturer").fill(item['brand'])
            field(page, r"^item cost with tax").fill(item['cost'])
            # Unknown model and serial numbers remain blank.
            save = visible_one(page.get_by_role("button", name=re.compile(r"^Save$", re.I)))
            save.click()
            try:
                save.wait_for(state="hidden", timeout=15000)
                visible_one(page.get_by_text(item['name'], exact=True)).wait_for(state="visible")
            except Exception:
                raise RuntimeError("Could not verify Save. Check the browser for validation errors or the saved card before rerunning; stopped to avoid duplicates.")
            saved.append(key)
            journal(saved)
            print("Saved. Local journal updated to help avoid duplicates on rerun.")
        print("\nFinished item entry. Review the claim in the browser. The script never clicks Continue or Submit.")
        input("Press Enter when you are ready to close this browser: ")
        browser.close()

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nStopped.")
    except Exception as exc:
        print(f"\nStopped: {exc}")
        print("If fields could not be found, share the Item Information form's HTML or field labels.")
        input("Press Enter after checking the browser/error: ")
        raise SystemExit(1)
