import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import io
import re
import zipfile

st.set_page_config(page_title="Image Scraper & Downloader", page_icon="🖼️", layout="wide")

DOWNLOAD_DIR = "downloaded_images"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".avif", ".tiff", ".ico"}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

BG_IMAGE_RE = re.compile(r"background-image\s*:\s*url\((['\"]?)(.*?)\1\)", re.IGNORECASE)


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except ValueError:
        return False


def get_extension(url: str, content_type: str = "") -> str:
    path = urlparse(url).path
    ext = os.path.splitext(path)[1].lower()
    if ext in VALID_EXTENSIONS:
        return ext

    content_type = content_type.lower()
    mapping = {
        "jpeg": ".jpg",
        "jpg": ".jpg",
        "png": ".png",
        "gif": ".gif",
        "webp": ".webp",
        "bmp": ".bmp",
        "svg": ".svg",
        "avif": ".avif",
        "tiff": ".tiff",
        "x-icon": ".ico",
        "vnd.microsoft.icon": ".ico",
    }
    for key, value in mapping.items():
        if key in content_type:
            return value
    return ".jpg"


def fetch_page(url: str, timeout: int = 10):
    """Fetch a page and return (soup, error_message). Only one will be non-None."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
    except requests.exceptions.MissingSchema:
        return None, "That URL looks invalid. Please include http:// or https://"
    except requests.exceptions.ConnectionError:
        return None, "Could not connect to this URL. Please check the address or your internet connection."
    except requests.exceptions.Timeout:
        return None, "The site took too long to respond. Please try again."
    except requests.exceptions.HTTPError as e:
        return None, f"The site returned an error and access was denied ({e})."
    except requests.exceptions.RequestException as e:
        return None, f"Could not access this URL ({e})."

    soup = BeautifulSoup(resp.text, "html.parser")
    return soup, None


def _best_from_srcset(srcset: str) -> str:
    """Given a srcset attribute string, return the highest-resolution URL."""
    candidates = []
    for part in srcset.split(","):
        part = part.strip()
        if not part:
            continue
        bits = part.split()
        url = bits[0]
        width = 0
        if len(bits) > 1 and bits[1].endswith("w"):
            try:
                width = int(bits[1][:-1])
            except ValueError:
                width = 0
        elif len(bits) > 1 and bits[1].endswith("x"):
            try:
                width = int(float(bits[1][:-1]) * 1000)
            except ValueError:
                width = 0
        candidates.append((width, url))
    if not candidates:
        return ""
    candidates.sort(key=lambda c: c[0], reverse=True)
    return candidates[0][1]


def extract_image_urls(soup, base_url):
    """
    Pulls image URLs from:
      - <img src>, data-src, data-lazy-src, srcset
      - <picture><source srcset> variants
      - inline style="background-image:url(...)" on any tag
      - <style> blocks containing background-image:url(...)
    Handles jpg, png, jpeg, gif, webp, svg, avif, bmp, ico, and extension-less
    (CDN-style) URLs alike — filtering by actual content-type happens later.
    """
    urls = []

    # Standard <img> tags
    for tag in soup.find_all("img"):
        src = tag.get("src") or tag.get("data-src") or tag.get("data-lazy-src")
        if src and not src.startswith("data:"):
            urls.append(src)

        srcset = tag.get("srcset") or tag.get("data-srcset")
        if srcset:
            best = _best_from_srcset(srcset)
            if best and not best.startswith("data:"):
                urls.append(best)

    # <picture><source srcset="..."></picture>
    for source_tag in soup.find_all("source"):
        srcset = source_tag.get("srcset")
        if srcset:
            best = _best_from_srcset(srcset)
            if best and not best.startswith("data:"):
                urls.append(best)

    # Inline style="background-image:url(...)"
    for tag in soup.find_all(style=True):
        match = BG_IMAGE_RE.search(tag["style"])
        if match:
            bg_url = match.group(2)
            if bg_url and not bg_url.startswith("data:"):
                urls.append(bg_url)

    # <style>...background-image:url(...)...</style> blocks
    for style_tag in soup.find_all("style"):
        if style_tag.string:
            for match in BG_IMAGE_RE.finditer(style_tag.string):
                bg_url = match.group(2)
                if bg_url and not bg_url.startswith("data:"):
                    urls.append(bg_url)

    # Resolve to absolute URLs and de-duplicate, preserving order
    seen, unique = set(), []
    for u in urls:
        full_url = urljoin(base_url, u.strip())
        if full_url not in seen:
            seen.add(full_url)
            unique.append(full_url)

    return unique


def download_images(image_urls, timeout, progress_callback=None):
    """
    Downloads images and saves them sequentially as 1.<ext>, 2.<ext>, ...
    Returns (downloaded_list, failed_list).
    """
    downloaded, failed = [], []
    total = len(image_urls)

    for i, img_url in enumerate(image_urls, start=1):
        try:
            r = requests.get(img_url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            content_type = r.headers.get("Content-Type", "")
            ext = get_extension(img_url, content_type)
            name = f"{i}{ext}"
            with open(os.path.join(DOWNLOAD_DIR, name), "wb") as f:
                f.write(r.content)
            downloaded.append({"name": name, "bytes": r.content, "source_url": img_url})
        except requests.exceptions.RequestException:
            failed.append(img_url)

        if progress_callback:
            progress_callback(i, total)

    return downloaded, failed


def make_zip(downloaded_images) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for img in downloaded_images:
            zf.writestr(img["name"], img["bytes"])
    buf.seek(0)
    return buf


# ---------------------------- UI ----------------------------
st.title("🖼️ Image Scraper & Downloader")
st.caption(
    "Paste any webpage URL, scrape every image on it (jpg, png, jpeg, gif, "
    "webp, svg, avif, CSS background images, and more), and save them to "
    "your device — works on desktop and mobile browsers."
)

with st.sidebar:
    st.header("Settings")
    max_images = st.number_input("Max images to fetch (0 = no limit)", min_value=0, value=0, step=1)
    timeout = st.slider("Request timeout (seconds)", 5, 30, 10)
    st.markdown("---")
    st.caption(
        "This app also keeps a copy in a local `downloaded_images/` folder "
        "on the machine running the app. If you're on a phone or a hosted "
        "deployment, that folder isn't yours — use the **Download ZIP** "
        "or per-image buttons below; those actually save to your device."
    )

url = st.text_input("Webpage URL", placeholder="https://example.com/gallery")
fetch_clicked = st.button("Fetch Images", type="primary")

if "downloaded" not in st.session_state:
    st.session_state.downloaded = []
if "failed" not in st.session_state:
    st.session_state.failed = []

if fetch_clicked:
    st.session_state.downloaded = []
    st.session_state.failed = []

    cleaned_url = url.strip()
    if not cleaned_url:
        st.warning("Please enter a URL first.")
    elif not is_valid_url(cleaned_url):
        st.error("That doesn't look like a valid URL. Make sure it starts with http:// or https://")
    else:
        with st.spinner("Accessing the page..."):
            soup, err = fetch_page(cleaned_url, timeout=timeout)

        if err:
            st.error(f"⚠️ {err}")
        else:
            image_urls = extract_image_urls(soup, cleaned_url)

            if not image_urls:
                st.info("No images were found on this page.")
            else:
                if max_images > 0:
                    image_urls = image_urls[:max_images]

                st.success(f"Found {len(image_urls)} image(s). Downloading...")
                progress = st.progress(0)
                status = st.empty()

                def update_progress(i, total):
                    progress.progress(i / total)
                    status.text(f"Downloading {i}/{total}")

                downloaded, failed = download_images(image_urls, timeout, progress_callback=update_progress)
                st.session_state.downloaded = downloaded
                st.session_state.failed = failed
                progress.empty()
                status.empty()

                if downloaded:
                    st.success(f"✅ Downloaded {len(downloaded)} image(s) successfully.")
                if failed:
                    st.warning(f"⚠️ {len(failed)} image(s) could not be downloaded (broken link or access blocked).")

# ---------------------------- Results ----------------------------
if st.session_state.downloaded:
    st.markdown("---")
    st.subheader("Downloaded Images")

    zip_buf = make_zip(st.session_state.downloaded)
    st.download_button(
        label=f"⬇️ Download all {len(st.session_state.downloaded)} images as ZIP",
        data=zip_buf,
        file_name="images.zip",
        mime="application/zip",
        type="primary",
    )

    cols = st.columns(4)
    for idx, img in enumerate(st.session_state.downloaded):
        with cols[idx % 4]:
            try:
                st.image(img["bytes"], caption=img["name"], use_container_width=True)
            except Exception:
                st.caption(f"{img['name']} (preview unavailable, e.g. .svg/.ico)")
            st.download_button(
                label=f"Save {img['name']}",
                data=img["bytes"],
                file_name=img["name"],
                mime="image/*",
                key=f"dl_{img['name']}_{idx}",
            )

if st.session_state.failed:
    with st.expander(f"⚠️ {len(st.session_state.failed)} failed download(s)"):
        for f_url in st.session_state.failed:
            st.text(f_url)