import json
import random
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse, urljoin
import html as html_std

import requests
from lxml import html

from dlsite_app.config import settings


def _with_affiliate_id(raw_url: str | None) -> str | None:
    if not raw_url:
        return None
    if "<iframe" in raw_url:
        src_match = re.search(r'src=["\\\']([^"\\\']+)', raw_url)
        if src_match:
            raw_url = src_match.group(1)
    parsed = urlparse(raw_url)
    query = parse_qs(parsed.query)
    query["aid"] = [settings.affiliate_id]
    new_query = urlencode(query, doseq=True)
    return urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment)
    )


def _find_chobit_url(text: str) -> str | None:
    """Pick the first chobit.cc URL from arbitrary text (iframe/html/textarea)."""
    # Unescape entities and normalize escaped slashes (\" \/ style)
    unescaped = html_std.unescape(text)
    normalized = unescaped.replace("\\/", "/")
    match = re.search(
        r"(https?://[^\s\"'>]*chobit\.cc[^\s\"'>]*)|(//[^\s\"'>]*chobit\.cc[^\s\"'>]*)",
        normalized,
        flags=re.IGNORECASE,
    )
    if match:
        url = match.group(0)
        if url.startswith("//"):
            url = "https:" + url
        return url
    return None


def _normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("//"):
        return "https:" + url
    return url


def _download_file(url: str, dest: Path):
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        return True
    except Exception as exc:
        print(f"Download failed {url}: {exc}")
        return False


def download_images(
    rj_code: str, main_url: str | None, sample_urls: list[str], image_root: Path, desc_urls: list[str] | None = None
):
    """Download main and sample images into images/{rj_code}/.

    desc_urls: optional list of description images; saved as desc_XX.ext for reference.
    """
    norm_main = _normalize_url(main_url)
    norm_samples = []
    for u in sample_urls:
        nu = _normalize_url(u)
        if not nu:
            continue
        if nu == norm_main:
            # Skip if identical to main to reduce duplicate fetches
            continue
        if nu in norm_samples:
            continue
        norm_samples.append(nu)
    base_dir = Path(image_root) / rj_code
    if norm_main:
        ext = Path(urlparse(norm_main).path).suffix or ".jpg"
        dest = base_dir / f"main{ext}"
        if not dest.exists():  # avoid re-downloading if already cached
            _download_file(norm_main, dest)
    for idx, url in enumerate(norm_samples, start=1):
        ext = Path(urlparse(url).path).suffix or ".jpg"
        dest = base_dir / f"sample_{idx:02d}{ext}"
        if dest.exists():
            continue
        _download_file(url, dest)

    # Description images (kept separate names to distinguish source)
    if desc_urls:
        norm_desc = []
        for u in desc_urls:
            nu = _normalize_url(u)
            if not nu:
                continue
            if nu in norm_desc:
                continue
            norm_desc.append(nu)
        for idx, url in enumerate(norm_desc, start=1):
            ext = Path(urlparse(url).path).suffix or ".jpg"
            dest = base_dir / f"desc_{idx:02d}{ext}"
            if dest.exists():
                continue
            _download_file(url, dest)


def _extract_chobit_embed(tree: html.HtmlElement, raw_text: str) -> str | None:
    """
    Try several patterns within a chobit page/search result:
    - <div class="embed-tag"><input value="...iframe...">
    - any iframe/src containing chobit.cc
    - any literal chobit.cc URL in the text
    """
    embed_input = tree.xpath("//div[@class='embed-tag']//input/@value")
    if embed_input:
        return _with_affiliate_id(embed_input[0])

    iframe_srcs = tree.xpath("//iframe[contains(@src, 'chobit.cc')]/@src")
    if iframe_srcs:
        return _with_affiliate_id(iframe_srcs[0])

    from_text = _find_chobit_url(raw_text)
    if from_text:
        # Avoid returning the search page itself
        if "/s/?" in from_text:
            return None
        return _with_affiliate_id(from_text)
    return None


def fetch_chobit_via_search(rj_code: str) -> str | None:
    """Search on chobit.cc by RJ code and pick the embed iframe src."""
    search_url = "https://chobit.cc/s/"
    params = {"f_category": "all", "q_keyword": rj_code}
    headers = {"User-Agent": "ASMR-Finder-Bot/1.0"}
    try:
        res = requests.get(search_url, params=params, headers=headers, timeout=10)
        res.raise_for_status()

        # If redirected to a work page directly, res.url will not be /s/
        tree = html.fromstring(res.content)
        found = _extract_chobit_embed(tree, res.text)
        if found:
            return found

        # If still on search results, try to follow the first work link
        links = tree.xpath("//a[@href and not(contains(@href,'/s/'))]/@href")
        work_links: list[str] = []
        for href in links:
            # heuristics: simple path like /abcd or /abc123
            if re.match(r"^/[A-Za-z0-9]{4,}$", href):
                work_links.append(href)
        if work_links:
            work_url = urljoin("https://chobit.cc", work_links[0])
            try:
                work_res = requests.get(work_url, headers=headers, timeout=10)
                work_res.raise_for_status()
                work_tree = html.fromstring(work_res.content)
                found_work = _extract_chobit_embed(work_tree, work_res.text)
                if found_work:
                    return found_work
            except Exception as inner_exc:
                print(f"[{rj_code}] Chobit work fetch error: {inner_exc}")

        return None
    except Exception as exc:
        print(f"[{rj_code}] Chobit search fetch error: {exc}")
        return None


def fetch_dynamic_data(rj_code: str, session: requests.Session | None = None):
    """Fetch dynamic metadata (DL count, price, etc.) via the AJAX endpoint."""
    client = session or requests
    url = "https://www.dlsite.com/maniax/product/info/ajax"
    params = {"product_id": rj_code, "cdn_cache_min": 1}
    headers = {
        "User-Agent": "ASMR-Finder-Bot/1.0",
        "Referer": f"https://www.dlsite.com/maniax/work/=/product_id/{rj_code}.html",
        "X-Requested-With": "XMLHttpRequest",
    }

    try:
        time.sleep(random.uniform(1, 3))
        res = client.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        work_data = res.json().get(rj_code)
        return work_data
    except Exception as exc:
        print(f"[{rj_code}] Dynamic data fetch error: {exc}")
        return None


def fetch_static_data(rj_code: str):
    """Fetch static metadata (title, circle, genres, description, etc.)."""
    url = f"https://www.dlsite.com/maniax/work/=/product_id/{rj_code}.html"
    headers = {
        "User-Agent": "ASMR-Finder-Bot/1.0",
        "Cookie": "adult_checked=1",  # age gate
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        tree = html.fromstring(res.content)

        data: dict[str, str | list[str] | None] = {}
        table_cache: dict[str, list[str]] = {}

        def uniq_urls(urls: list[str]) -> list[str]:
            seen = set()
            out = []
            for u in urls:
                if not u:
                    continue
                if u.startswith("//"):
                    u = "https:" + u
                if u in seen:
                    continue
                seen.add(u)
                out.append(u)
            return out

        def get_table_val(label: str) -> list[str]:
            if label in table_cache:
                return table_cache[label]
            val = tree.xpath(f"//table[@id='work_outline']//tr[th[contains(text(),'{label}')]]/td/a/text()")
            if not val:
                val = tree.xpath(f"//table[@id='work_outline']//tr[th[contains(text(),'{label}')]]/td/text()")
            cleaned = [v.strip() for v in val if v and v.strip()]
            table_cache[label] = cleaned
            return cleaned

        title = tree.xpath("//h1[@id='work_name']/text()")
        data["title"] = title[0] if title else None

        circle = tree.xpath("//span[@class='maker_name']//a/text()")
        data["circle"] = circle[0] if circle else None

        desc_section = tree.xpath("/html/body/div[3]/div[4]/div[1]/div/div[3]")
        if not desc_section:
            desc_section = tree.xpath("//div[contains(@class, 'work_parts_container')]")
        desc_root = desc_section[0] if desc_section else None

        data["description"] = "\n".join(desc_root.itertext()).strip() if desc_root is not None else None
        desc_images: list[str] = []
        if desc_root is not None:
            for img in desc_root.xpath(".//img"):
                src = img.get("src") or img.get("data-src")
                if src:
                    desc_images.append(src)
        content_tokens: list[dict] = []
        if desc_root is not None:
            def add_text(txt: str):
                if txt and txt.strip():
                    content_tokens.append({"type": "text", "content": txt})

            for elem in desc_root.iter():
                if elem.text:
                    add_text(elem.text)
                if elem.tag == "img":
                    img_src = elem.get("src") or elem.get("data-src")
                    if img_src:
                        norm_img = img_src if not img_src.startswith("//") else "https:" + img_src
                        content_tokens.append({"type": "image", "url": norm_img})
                if elem.tail:
                    add_text(elem.tail)
        data["content_tokens"] = content_tokens

        release_date = get_table_val("販売日")
        data["release_date"] = release_date[0] if release_date else None
        data["cv"] = get_table_val("声優")
        data["age_limit"] = get_table_val("年齢指定")
        data["work_type"] = get_table_val("作品形式")
        data["file_format"] = get_table_val("ファイル形式")
        data["genres"] = tree.xpath("//div[@class='main_genre']//a/text()")

        file_size = tree.xpath("//table[@id='work_outline']//tr[th[contains(text(),'ファイル容量')]]/td/div/text()")
        data["file_size"] = file_size[0].strip() if file_size else None

        # Chobit Integration (main page iframe -> fallback to any chobit URL)
        data["chobit_url"] = None
        chobit_iframe = tree.xpath("//iframe[contains(@src, 'chobit.cc')]/@src")
        if chobit_iframe:
            data["chobit_url"] = _with_affiliate_id(chobit_iframe[0])
        if not data["chobit_url"]:
            raw_from_body = _find_chobit_url(res.text)
            if raw_from_body:
                data["chobit_url"] = _with_affiliate_id(raw_from_body)
        # As a last resort, try the affiliate tool page (opt-in via env to avoid extra requests)
        if not data["chobit_url"] and settings.enable_chobit_affiliate_fallback:
            aff_url = f"https://www.dlsite.com/maniax/dlaf/tool/=/work_id/{rj_code}"
            try:
                aff_res = requests.get(aff_url, headers=headers, timeout=10)
                if aff_res.ok:
                    raw_from_aff = _find_chobit_url(aff_res.text)
                    if raw_from_aff:
                        data["chobit_url"] = _with_affiliate_id(raw_from_aff)
            except Exception as exc:
                print(f"[{rj_code}] Chobit fallback fetch error: {exc}")
        # Chobit search page as another fallback
        if not data["chobit_url"] and settings.enable_chobit_search:
            data["chobit_url"] = fetch_chobit_via_search(rj_code)

        # Media (sample images) from slider (preferred) or fallback path
        sample_urls: list[str] = []
        slider_data = tree.xpath("//div[@id='product_slider_data'] | //div[contains(@class, 'product-slider-data')]")
        if slider_data:
            for div in slider_data[0].xpath(".//div[@data-src]"):
                src = div.get("data-src")
                if src:
                    sample_urls.append(src)
        # Explicit fallback path provided by user
        sample_fallback = tree.xpath("/html/body/div[3]/div[4]/div[1]/div/div[1]/div[1]//img")
        for img in sample_fallback:
            src = img.get("data-src") or img.get("src")
            if src:
                sample_urls.append(src)

        sample_urls = uniq_urls(sample_urls)
        desc_images = uniq_urls(desc_images)
        # Avoid downloading the same file twice across sample/desc
        sample_set = set(sample_urls)
        desc_images = [u for u in desc_images if u not in sample_set]

        data["media"] = sample_urls
        data["desc_images"] = desc_images

        return data

    except Exception as exc:
        print(f"[{rj_code}] Static data fetch error: {exc}")
        return {}


def save_work_to_json(
    rj_code: str,
    output_dir: Path | None = None,
    download_media: bool = False,
    image_root: Path | None = None,
    chobit_only: bool = False,
) -> bool:
    """Fetch data for a single RJ code and persist to JSON.

    - If chobit_only=True, only static page fetch is performed (for chobit embed and metadata).
    - If download_media=True, main and sample images are downloaded to image_root/rj_code/.
    """
    output_dir = Path(output_dir or settings.data_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing: {rj_code}")
    static_data = fetch_static_data(rj_code)
    dynamic_data = {} if chobit_only else fetch_dynamic_data(rj_code)

    if not static_data and not dynamic_data:
        print(f"Failed to fetch any data for {rj_code}")
        return False

    full_data = {
        "rj_code": rj_code,
        "scraped_at_ts": time.time(),
        "static_info": static_data,
        "dynamic_info": dynamic_data if dynamic_data else {},
    }

    filename = output_dir / f"{rj_code}.json"
    with filename.open("w", encoding="utf-8") as f:
        json.dump(full_data, f, ensure_ascii=False, indent=4)

    if download_media:
        main_img = dynamic_data.get("work_image") if dynamic_data else None
        desc_imgs = static_data.get("desc_images", [])
        samples = static_data.get("media", []) if static_data else []
        # Avoid re-downloading desc images as samples
        if desc_imgs:
            samples = [url for url in samples if url not in set(desc_imgs)]
        download_images(
            rj_code,
            main_img,
            samples,
            image_root or settings.image_root,
            desc_urls=desc_imgs,
        )

    print(f"Saved successfully: {filename}")
    return True


def load_works(filepath: str | Path = "works.txt") -> list[str]:
    """Load RJ codes from a text file, deduplicate, and write back normalized order."""
    path = Path(filepath)
    if not path.exists():
        return []

    lines = path.read_text(encoding="utf-8").splitlines()
    unique_codes = sorted(list({line.strip() for line in lines if line.strip().startswith("RJ")}))
    path.write_text("\n".join(unique_codes), encoding="utf-8")
    return unique_codes


def scrape_from_file(works_file: str | Path = "works.txt", output_dir: Path | None = None):
    """Scrape all RJ codes listed in works_file."""
    print(f"Loading targets from {works_file}...")
    targets = load_works(works_file)
    print(f"Found {len(targets)} unique works.")

    for code in targets:
        save_work_to_json(code, output_dir=output_dir)
        time.sleep(random.uniform(2, 5))
