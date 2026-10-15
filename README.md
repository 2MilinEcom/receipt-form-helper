# Receipt Form Helper

I built this helper to turn receipt screenshots into details I can review before filling a form. I kept the browser extension separate from the local Python service so account access stays in my normal browser.

I used JavaScript for the extension and Python for image processing and extraction. I can correct the extracted details before filling a form, and the helper leaves final submission to me.

## Running it

I install `requirements.txt` in a Python environment, configure my own settings from `.env.example`, and run `python local_server.py`. I load `chrome_extension/` as an unpacked extension in Chrome.

I use fictional receipt images when demonstrating the project. I keep credentials and saved receipt records outside version control. I kept the detailed local workflow in `README.txt`.
