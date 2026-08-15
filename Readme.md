# Image Scraper & Downloader (Streamlit)

Paste any webpage URL, the app scrapes **every image on that page** — not
just plain `<img src="...jpg">` tags — downloads them, and lets you save
them individually or as one ZIP, straight to whatever device you're using
(laptop, phone, tablet).

## 🔗 Live App

**[https://image-scraper-pawan.streamlit.app/](https://image-scraper-pawan.streamlit.app/)**

No install needed — open this link on your phone, tablet, or laptop
(any device, any network) and start scraping right away.

## Files
- `app.py` — the full Streamlit app
- `requirements.txt` — dependencies

## What image formats/sources it handles

**Formats:** `.jpg` / `.jpeg`, `.png`, `.gif`, `.webp`, `.svg`, `.avif`,
`.bmp`, `.tiff`, `.ico`, and extension-less CDN-style URLs (the app reads
the server's `Content-Type` header to figure out the real format in that
case).

**HTML sources it scans:**
- `<img src="...">`
- `<img data-src="...">` / `data-lazy-src` (common on lazy-loaded galleries)
- `<img srcset="...">` (picks the highest-resolution candidate)
- `<picture><source srcset="..."></picture>` (responsive/modern image markup)
- Inline `style="background-image:url(...)"` on any element
- `background-image:url(...)` inside `<style>` blocks

Everything found is resolved to a full absolute URL (relative paths like
`/images/pic.png` are joined against the page's own address), de-duplicated,
then downloaded and renamed sequentially as `1.<ext>`, `2.<ext>`, `3.<ext>`, …
with each file keeping **its own correct extension** — a mixed page can
produce `1.jpg`, `2.png`, `3.webp`, `4.svg` all in one run.

## Option A: Just use the live app

Go to **[https://image-scraper-pawan.streamlit.app/](https://image-scraper-pawan.streamlit.app/)**
from any device's browser — nothing to install. Skip straight to
[How it works](#how-it-works) below.

## Option B: Run it yourself

### 1. Install

```bash
pip install -r requirements.txt
```

### 2. Run locally

```bash
streamlit run app.py
```

This opens `http://localhost:8501` in your browser.

### 3. Use it from your phone (same Wi-Fi)

Run it bound to your network IP instead of just localhost:

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Find your computer's local IP (e.g. `192.168.1.23`) and on your phone's
browser (same Wi-Fi network) go to:

```
http://192.168.1.23:8501
```

### 4. Deploy your own copy

For access from any device/network, deploy it (all have free tiers):
- **Streamlit Community Cloud** — connect this repo, one click deploy.
  (This is what powers the live app linked above.)
- **Render / Railway / Hugging Face Spaces** — also support Streamlit apps directly.

Once deployed you'll get a public URL you can open from any phone or computer.

## How it works

1. Enter a webpage URL (must start with `http://` or `https://`).
2. Click **Fetch Images** — the app requests the page, parses it with
   BeautifulSoup, and pulls image references from all the sources listed
   above.
3. Each image is downloaded and renamed sequentially: `1.jpg`, `2.png`,
   `3.webp`, … (extension detected from the URL or the response's
   `Content-Type`).
4. A copy is saved server-side to a `downloaded_images/` folder (useful if
   you're running this on your own machine) **and** you get browser
   **Download** buttons — those are what actually push files to your
   phone/tablet/laptop's Downloads folder, since a browser can't write to a
   remote server's disk directly.

## Error handling

If a URL can't be reached, isn't valid, blocks the request, times out, or
simply has no images, the app shows a plain, clear message instead of
crashing — e.g.:
- "That doesn't look like a valid URL..."
- "Could not connect to this URL..."
- "The site returned an error and access was denied..."
- "No images were found on this page."

Individual images that fail to download (broken links, blocked hotlinking,
etc.) are listed separately in an expandable "failed downloads" section
instead of stopping the whole batch. Formats without a browser preview
(like `.svg` or `.ico` in some cases) still download fine — the app just
shows a text caption instead of a broken preview.

## Notes / limitations

- Some sites block scraping via `robots.txt` or server-side checks
  (Cloudflare, login walls, etc.) — the app will report these as access
  errors rather than silently failing.
- Images loaded purely by JavaScript *after* the page finishes loading
  (no reference anywhere in the raw HTML/CSS) need a headless-browser tool
  (e.g. Selenium/Playwright) instead of `requests`, which this project
  intentionally keeps lightweight. Everything present in the page's HTML
  or inline/`<style>` CSS — including lazy-load attributes and responsive
  `srcset`/`<picture>` markup — is covered.
- Please only scrape sites you have the right to scrape, and respect their
  terms of service and copyright on any images you download.

## Author

**Pawan Yadav** — AI Engineer
📧 yaduvanshi2000pawan@gmail.com
