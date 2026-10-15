NORMAL-CHROME EXTENSION (recommended when the automated browser cannot log in)

1. Keep your .env API key and existing .venv. From this folder:
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   python local_server.py
   Leave Terminal running. It opens no browser and handles no Amex login.

2. In your NORMAL Chrome, open chrome://extensions.
   Turn on Developer mode, click Load unpacked, and select the chrome_extension
   subfolder inside amex_claim_helper. This is a one-time local installation.
   When updating the extension files, click Reload on its extensions card.

3. Log in to Amex normally and open your existing claim at Item Information.
   Save your headphones first. Open a NEW blank clothing item.
   Click the Extensions puzzle icon, then Amex Clothing Helper.

4. In the helper tab, drag receipt screenshots into the box and click
   Read screenshots. Correct the combined review if needed. Select your
   existing claims tab and click Fill and save included clothing in that tab.
   The extension selects dropdowns using your local OpenAI helper.
   Return to the helper tab if you need to see a completion/error message.

5. Review the saved entries. Final claim submission is yours.

The extension has access only to the Amex claims site and the local receipt
helper, plus local storage for saved-item duplicate prevention. It does not
access Amex login pages, passwords, card details, or cookies. Only selected
receipt images and dropdown option labels are sent to OpenAI. Your API key
stays in Python/.env and is not sent to the extension or saved in Chrome.
The local server listens on 127.0.0.1:18765 and accepts extension-origin requests.
Keep .env private; it is excluded from the distributed ZIP.

Missing dates remain blank. Unknown brands are labelled Unknown. When item
 tax is not evidenced, the visible base amount is used and tax excluded, with
 a note in the review. You can replace it with a verified tax-inclusive total.
Mixed-order tax is never apportioned automatically. Verify AI extraction.
The five clothing items discussed are included; headphones are omitted.

Duplicate tracking is saved in the extension's local storage. After a Save
failure or interruption, inspect the actual claim before retrying. A Save
that completed before a validation timeout may not have been journaled.
The helper does not click Continue or Submit. Do not use repeated Fill clicks
without checking previously saved entries.

Validation checked locally: extension JavaScript syntax, receipt service
request handling, and extraction safeguards. No live Amex form or API call
was tested. Different labels/custom dropdowns may need adjustments; share
redacted item form HTML/labels if filling fails. Login problems in an automated
browser are not proven to be bot blocking; this extension uses the normal
Chrome session you already report works, without attempting to evade controls.

LEGACY AUTOMATED-BROWSER VERSION
python claim_helper.py still runs the earlier browser helper. Use
python local_server.py with the extension for normal-Chrome operation.

LOCAL DRAFT STORAGE
The extension saves receipt images and edited review rows in its local IndexedDB storage. Reopening or reloading the same installed extension restores them without another OpenAI request. Use Fill directly with a restored review. Keep the extension installed at the same folder path; removing it or clearing its browser storage removes the draft. The Forget saved screenshots and review button deletes the draft, but does not change saved Amex entries.

ADDING MORE PRODUCTS
Drop new receipt screenshots and click Read screenshots. New products are appended unchecked to your saved review; existing review details are preserved. Check the products actually stolen and complete any missing evidence-backed fields. The helper supports merchandise beyond clothing, including headphones, using the available Amex categories. Restored reviews need no new reading.
