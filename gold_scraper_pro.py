#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   22 Ayar Gold Bracelet (Bilezik) — Advanced Price Comparison Scraper PRO   ║
║   Sites  : Hepsiburada · Amazon Turkey · N11 · Idefix                       ║
║   Engine : Playwright (headless Chromium) + User-Agent rotation             ║
║   Output : Per-weight comparison table + Price-per-gram + Best Deal finder  ║
╚══════════════════════════════════════════════════════════════════════════════╝

─── Quick Start ───────────────────────────────────────────────────────────────
  pip3 install -r requirements.txt
  python3 -m playwright install chromium
  python3 gold_scraper_pro.py
───────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

try:
    import requests as _requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

# ── Optional pretty-print libs (graceful fallback) ────────────────────────────
try:
    from tabulate import tabulate
    TABULATE_OK = True
except ImportError:
    TABULATE_OK = False

try:
    from colorama import Fore, Style, init as _cinit
    _cinit(autoreset=True)
    C_GREEN  = Fore.GREEN
    C_YELLOW = Fore.YELLOW
    C_RED    = Fore.RED
    C_CYAN   = Fore.CYAN
    C_RESET  = Style.RESET_ALL
    C_BOLD   = Style.BRIGHT
    COLOR_OK = True
except ImportError:
    C_GREEN = C_YELLOW = C_RED = C_CYAN = C_RESET = C_BOLD = ""
    COLOR_OK = False

try:
    from playwright.async_api import (
        async_playwright,
        Browser,
        BrowserContext,
        Page,
        TimeoutError as PWTimeout,
    )
    PW_OK = True
except ImportError:
    PW_OK = False

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("gold_scraper")


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION — Add your product URLs here
# ══════════════════════════════════════════════════════════════════════════════

PRODUCT_URLS: Dict[str, List[dict]] = {

    # ── 5 GRAM ────────────────────────────────────────────────────────────────
    "5g": [
        # Hepsiburada
        {"url": "https://www.hepsiburada.com/5-gr-22-ayar-oluklu-ajda-bilezik-pm-HBC0000BDNGBE",           "site": "Hepsiburada"},
        {"url": "https://www.hepsiburada.com/22-ayar-italyan-model-5-gr-bilezik-pm-HBC000014EVUT",         "site": "Hepsiburada"},
        # Amazon TR
        {"url": "https://www.amazon.com.tr/AgaKulche-Gram-Ayar-Ajda-Bilezik/dp/B0FBJX4LH6",               "site": "Amazon TR"},
        # N11
        {"url": "https://www.n11.com/urun/kavafzade-5-gram-22-ayar-kibrit-copu-yatirimlik-isciliksiz-bilezik-76174762", "site": "N11"},
        {"url": "https://www.n11.com/urun/t51tugrulaltin-5-grgram-22-ayar-kibrit-copu-bilezik-370259912-22094656",      "site": "N11"},
        # Idefix
        {"url": "https://www.idefix.com/5-gr-gram-22-ayar-ajda-bilezik-p-16587034",                        "site": "Idefix"},
        {"url": "https://www.idefix.com/kado-kuyumculuk-5-gr-gram-22-ayar-zikzak-ajda-bilezik-p-14932657", "site": "Idefix"},
    ],

    # ── 10 GRAM ───────────────────────────────────────────────────────────────
    "10g": [
        # Hepsiburada
        {"url": "https://www.hepsiburada.com/ahlatci-10-gr-22-ayar-ajda-bilezik-pm-HBC000012R16E",         "site": "Hepsiburada"},
        {"url": "https://www.hepsiburada.com/ahlatci-10-gr-22-ayar-sarnelli-bilezik-pm-HBC000012R16Q",     "site": "Hepsiburada"},
        # Amazon TR
        {"url": "https://www.amazon.com.tr/AgaKulche-Gram-Ayar-Ajda-Bilezik/dp/B0F1YWKCQF",               "site": "Amazon TR"},
        {"url": "https://www.amazon.com.tr/i%C5%9F%C3%A7iliksiz-Parlak-Bilezik-Ziynet-Gold/dp/B0CV7GXRRL","site": "Amazon TR"},
        # N11
        {"url": "https://www.n11.com/urun/10-gr-gram-22-ayar-ajda-bilezik-aajd10-54988148",                "site": "N11"},
        {"url": "https://www.n11.com/urun/22-ayar-10-gram-ajda-bilezik-19290476",                          "site": "N11"},
        # Idefix
        {"url": "https://www.idefix.com/anadolum-altin-10-gr-22-ayar-ajda-bilezik-p-12912190",             "site": "Idefix"},
        {"url": "https://www.idefix.com/10-grgram-22-ayar-isciliksiz-ajda-bilezik-p-6917062",              "site": "Idefix"},
    ],

    # ── 15 GRAM ───────────────────────────────────────────────────────────────
    "15g": [
        # Hepsiburada
        {"url": "https://www.hepsiburada.com/22-ayar-15-gr-ajda-bilezik-bzk164-pm-HBC00005OWRPA",          "site": "Hepsiburada"},
        {"url": "https://www.hepsiburada.com/ahlatci-15-gr-22-ayar-sarnelli-bilezik-pm-HBC000012R173",     "site": "Hepsiburada"},
        # Amazon TR
        {"url": "https://www.amazon.com.tr/i%C5%9F%C3%A7iliksiz-Bilezik-Ziynet-Gold-ZG2038/dp/B0CV7GKKK2","site": "Amazon TR"},
        {"url": "https://www.amazon.com.tr/Z%C3%9CMR%C3%9CT-SARRAF-Yat%C4%B1r%C4%B1ml%C4%B1k-Bilezik-VRTBlz0024/dp/B0DJVB36TZ", "site": "Amazon TR"},
        # N11
        {"url": "https://www.n11.com/urun/22-ayar-mujde-ajda-bilezik-15-gr-110696727",                     "site": "N11"},
        {"url": "https://www.n11.com/urun/22-ayar-altin-15-gram-ajda-bilezik-85773768",                    "site": "N11"},
        # Idefix
        {"url": "https://www.idefix.com/15-grgram-15-mm-22-ayar-isciliksiz-bilezik-p-6916749",             "site": "Idefix"},
        {"url": "https://www.idefix.com/15-grgram-15-mm-22-ayar-isciliksiz-duz-trabzon-bilezik-p-6917296", "site": "Idefix"},
    ],

    # ── 20 GRAM ───────────────────────────────────────────────────────────────
    "20g": [
        # Hepsiburada
        {"url": "https://www.hepsiburada.com/ahlatci-20-gr-3-lu-burma-22-ayar-bilezik-pm-HBC000012R15R",   "site": "Hepsiburada"},
        {"url": "https://www.hepsiburada.com/22-ayar-sarnel-20-gr-bilezik-blk1307-pm-HBC000014EVNU",       "site": "Hepsiburada"},
        # Amazon TR
        {"url": "https://www.amazon.com.tr/AgaKulche-Kanal-Alt%C4%B1n-Bilezik-Renkli/dp/B0F1YV3R3F",      "site": "Amazon TR"},
        # N11
        {"url": "https://urun.n11.com/22-ayar-bilezik/22-ayar-isciliksiz-simli-bilezik-20-gr-P464377122",  "site": "N11"},
        {"url": "https://urun.n11.com/22-ayar-bilezik/20-grgram-18-mm-22-ayar-isciliksiz-bilezik-tbc0020-2-P498601063", "site": "N11"},
        # Idefix
        {"url": "https://www.idefix.com/20-grgram-22-ayar-isciliksiz-bilezik-p-6917327",                   "site": "Idefix"},
        {"url": "https://www.idefix.com/20-grgram-20-mm-22-ayar-isciliksiz-bilezik-p-6917426",             "site": "Idefix"},
    ],
}

# ── Behaviour knobs ───────────────────────────────────────────────────────────
MIN_DELAY_SEC  = 2.0      # minimum pause between page loads (seconds)
MAX_DELAY_SEC  = 5.0      # maximum pause between page loads (seconds)
PAGE_TIMEOUT   = 35_000   # Playwright navigation timeout (ms)
HEADLESS       = True     # set False to watch the browser while debugging

# Sanity guard — overwritten at startup by fetch_live_gold_price_try().
# Fallback: 5,500 TRY/g (conservative lower bound, well below market).
# Actual threshold = live_22ayar_price × SANITY_RATIO (e.g. 0.88 = allow 12% below market).
MIN_PRICE_PER_GRAM_TRY: float = 5_500.0
MAX_PRICE_PER_GRAM_TRY: float = 50_000.0  # upper bound — also overwritten at startup
SANITY_RATIO           : float = 0.88   # products priced below 88% of market are rejected
MAX_SANITY_RATIO       : float = 2.50   # products priced above 250% of market are rejected

# Weight as integer grams — used for price-per-gram calculation
WEIGHT_GRAMS: Dict[str, int] = {"5g": 5, "10g": 10, "15g": 15, "20g": 20}

# ── User-Agent pool (desktop Chrome / Edge / Firefox) ─────────────────────────
USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",
]


# ══════════════════════════════════════════════════════════════════════════════
#  DATA MODEL
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Product:
    site:      str
    name:      str
    weight:    str
    price:     Optional[float]
    price_pgr: Optional[float] = None
    currency:  str = "TRY"
    url:       str = ""
    seller:    str = ""       # merchant/seller name (e.g. "Ahlatcı", "AgaKulche")
    status:    str = "ok"     # ok | out_of_stock | price_not_found | error
    error_msg: str = ""

    def __post_init__(self):
        grams = WEIGHT_GRAMS.get(self.weight)
        if self.price and grams:
            self.price_pgr = round(self.price / grams, 2)


# ══════════════════════════════════════════════════════════════════════════════
#  UTILITY HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def site_from_url(url: str) -> str:
    domain = urlparse(url).netloc.lower().replace("www.", "")
    for key, name in {
        "hepsiburada.com": "Hepsiburada",
        "amazon.com.tr":   "Amazon TR",
        "n11.com":         "N11",
        "idefix.com":      "Idefix",
    }.items():
        if key in domain:
            return name
    return domain.split(".")[0].capitalize()


def parse_try_price(raw: str) -> Optional[float]:
    """Parse Turkish / international price strings to float."""
    if not raw:
        return None
    cleaned = re.sub(r"[TL₺\s\u00a0\u202f]", "", raw.strip())
    cleaned = re.sub(r"[^\d.,]", "", cleaned)
    if not cleaned:
        return None
    dot_cnt   = cleaned.count(".")
    comma_cnt = cleaned.count(",")
    if dot_cnt == 1 and comma_cnt == 1:
        if cleaned.index(".") < cleaned.index(","):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif dot_cnt > 1:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif comma_cnt > 1:
        cleaned = cleaned.replace(",", "")
    elif comma_cnt == 1 and dot_cnt == 0:
        parts = cleaned.split(",")
        cleaned = cleaned.replace(",", "") if len(parts[1]) == 3 else cleaned.replace(",", ".")
    try:
        v = float(cleaned)
        return v if v > 0 else None
    except ValueError:
        return None


def sanity_check(price: Optional[float], weight: str) -> Optional[float]:
    """Return None if price is implausibly low OR absurdly high for 22-ayar gold."""
    if price is None:
        return None
    grams = WEIGHT_GRAMS.get(weight, 1)
    per_gram = price / grams
    if per_gram < MIN_PRICE_PER_GRAM_TRY:
        log.debug(f"  Sanity-failed (too low)  {price} for {weight} "
                  f"({per_gram:.0f} TRY/g < min {MIN_PRICE_PER_GRAM_TRY:.0f})")
        return None
    if per_gram > MAX_PRICE_PER_GRAM_TRY:
        log.debug(f"  Sanity-failed (too high) {price} for {weight} "
                  f"({per_gram:.0f} TRY/g > max {MAX_PRICE_PER_GRAM_TRY:.0f})")
        return None
    return price


def random_delay() -> None:
    delay = random.uniform(MIN_DELAY_SEC, MAX_DELAY_SEC)
    log.debug(f"  ⏳ Waiting {delay:.1f}s …")
    time.sleep(delay)


def truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def fmt_price(price: Optional[float], currency: str = "TRY") -> str:
    if price is None:
        return "N/A"
    s = f"{price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} {currency}"


def hyperlink(url: str, text: str) -> str:
    """
    OSC 8 clickable terminal hyperlink — FULL URL always used as target.
    Only the visible label (text) may be shortened.
    Supported: iTerm2, macOS Terminal 3.4+, Windows Terminal, VS Code terminal.
    ESC = \\x1b, BEL = \\x07  (BEL terminator is more widely compatible than ST)
    """
    return f"\x1b]8;;{url}\x07{text}\x1b]8;;\x07"


# ══════════════════════════════════════════════════════════════════════════════
#  JSON-LD + META FALLBACK HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _json_ld_price(html: str) -> Optional[float]:
    for m in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.S | re.I,
    ):
        try:
            data = json.loads(m.group(1))
        except (json.JSONDecodeError, ValueError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            offers = item.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            raw = (offers.get("price") if isinstance(offers, dict) else None) or item.get("price")
            if raw is not None:
                val = parse_try_price(str(raw))
                if val:
                    return val
    return None


def _meta_price(html: str) -> Optional[float]:
    for pat in [
        r'<meta[^>]+property=["\']product:price:amount["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+itemprop=["\']price["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']price["\'][^>]+content=["\']([^"\']+)["\']',
    ]:
        mm = re.search(pat, html, re.I)
        if mm:
            val = parse_try_price(mm.group(1))
            if val:
                return val
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  SITE-SPECIFIC PARSERS
# ══════════════════════════════════════════════════════════════════════════════

def fetch_hb_html_requests(url: str) -> Optional[str]:
    """
    Fetch a Hepsiburada page using the requests library instead of Playwright.
    Headless Chrome triggers HB's bot detection; a plain HTTP request with a
    realistic browser User-Agent often bypasses it.
    Returns the HTML string, or None on failure.
    """
    if not REQUESTS_OK:
        return None
    try:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": ("text/html,application/xhtml+xml,application/xml;"
                       "q=0.9,image/avif,image/webp,*/*;q=0.8"),
            "Accept-Language":           "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding":           "gzip, deflate, br",
            "DNT":                       "1",
            "Connection":                "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest":            "document",
            "Sec-Fetch-Mode":            "navigate",
            "Sec-Fetch-Site":            "none",
            "Sec-Ch-Ua":                 '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile":          "?0",
            "Sec-Ch-Ua-Platform":        '"Windows"',
        }
        r = _requests.get(url, headers=headers, timeout=20, allow_redirects=True)
        r.raise_for_status()
        html = r.text
        has_app = "__PRODUCT_DETAIL_APP__" in html
        has_price = bool(re.search(r'data-test-id="(checkout-price|price)"', html))
        log.info(f"  📡 HB requests fallback — "
                 f"PRODUCT_APP={'✓' if has_app else '✗'}  "
                 f"price-element={'✓' if has_price else '✗'}  "
                 f"size={len(html):,}b")
        return html
    except Exception as e:
        log.debug(f"  HB requests fallback failed: {e}")
        return None


def fetch_amazon_requests(url: str) -> Optional[str]:
    """
    Fetch an Amazon TR product page via plain HTTP requests (no Playwright).
    Amazon sometimes serves a lighter page to non-JS clients that still contains
    price data in a-offscreen spans or JSON-LD.
    Returns the HTML string, or None on failure.
    """
    if not REQUESTS_OK:
        return None
    try:
        # Extract ASIN from URL for a clean dp URL
        m_asin = re.search(r'/dp/([A-Z0-9]{10})', url)
        clean_url = f"https://www.amazon.com.tr/dp/{m_asin.group(1)}" if m_asin else url

        headers = {
            "User-Agent":    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                             "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept":        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT":           "1",
            "Connection":    "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }
        r = _requests.get(clean_url, headers=headers, timeout=20, allow_redirects=True)
        r.raise_for_status()
        html = r.text
        is_captcha  = bool(re.search(r'robot_check|Type the characters|captcha', html, re.I))
        has_offscr  = 'a-offscreen' in html
        has_buybox  = 'id="buybox"' in html or 'id="add-to-cart-button"' in html
        log.info(f"  📡 Amazon requests — "
                 f"captcha={'⚠' if is_captcha else '✗'}  "
                 f"buybox={'✓' if has_buybox else '✗'}  "
                 f"a-offscreen={'✓' if has_offscr else '✗'}  "
                 f"size={len(html):,}b")
        return html
    except Exception as e:
        log.debug(f"  Amazon requests fallback failed: {e}")
        return None


def _deep_find_price(obj, weight: str, depth: int = 0) -> Optional[float]:
    """
    Recursively walk any JSON structure to find a sane price value.
    Tries keys like price, listPrice, salePrice, discountedPrice, cartPrice, amount.
    Returns the first value that passes sanity_check.
    """
    if depth > 8:
        return None
    price_keys = {
        "price", "listprice", "saleprice", "discountedprice", "cartprice",
        "amount", "sellingprice", "displayprice", "formattedprice",
        "currentprice", "newprice",
    }
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = k.lower()
            if kl in price_keys and v is not None:
                val = parse_try_price(str(v))
                checked = sanity_check(val, weight)
                if checked:
                    return checked
        for v in obj.values():
            if isinstance(v, (dict, list)):
                found = _deep_find_price(v, weight, depth + 1)
                if found:
                    return found
    elif isinstance(obj, list):
        for item in obj:
            found = _deep_find_price(item, weight, depth + 1)
            if found:
                return found
    return None


def _deep_find_seller(obj, depth: int = 0) -> str:
    """Recursively find a merchant/seller name in JSON."""
    if depth > 8:
        return ""
    seller_keys = {
        "merchantname", "sellername", "merchant_name", "seller_name",
        "sellerdisplayname", "merchantdisplayname", "brandname",
        "merchantseoname",
    }
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in seller_keys and isinstance(v, str) and 2 <= len(v) <= 80:
                return v.strip()
        for v in obj.values():
            if isinstance(v, (dict, list)):
                found = _deep_find_seller(v, depth + 1)
                if found:
                    return found
    elif isinstance(obj, list):
        for item in obj:
            found = _deep_find_seller(item, depth + 1)
            if found:
                return found
    return ""


def fetch_hb_api_price(url: str, weight: str) -> Tuple[Optional[float], str]:
    """
    Try Hepsiburada's internal JSON APIs to get price + seller WITHOUT Playwright.
    HB serves JSON from several undocumented API endpoints that are far less
    aggressively rate-limited than the product page itself.

    Extracts the product SKU from the URL (suffix after -pm-) and queries:
      1. /product-service/api/products?ids={sku}           (product catalogue)
      2. /listing/api/listing?q=&productIds={sku}&take=1   (listing service)

    Returns (price, seller_name).  price=None on failure.
    """
    if not REQUESTS_OK:
        return None, ""

    m = re.search(r'-pm-([A-Z0-9]+)(?:/.*)?$', url)
    if not m:
        log.debug("  HB API: cannot extract SKU from URL")
        return None, ""

    sku = m.group(1)
    log.info(f"  🔑 HB product SKU: {sku}")

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept":          "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer":         url,
        "Origin":          "https://www.hepsiburada.com",
        "X-Requested-With": "XMLHttpRequest",
    }

    endpoints = [
        f"https://www.hepsiburada.com/product-service/api/products?ids={sku}",
        f"https://www.hepsiburada.com/listing/api/listing?q=&productIds={sku}&take=1&channel=web",
        f"https://www.hepsiburada.com/product-service/api/products/sku/{sku}",
        f"https://www.hepsiburada.com/product-service/api/products/{sku}",
    ]

    for ep in endpoints:
        try:
            r = _requests.get(ep, headers=headers, timeout=12, allow_redirects=True)
            log.info(f"  HB API [{r.status_code}] {ep[:80]}")
            if r.status_code != 200:
                continue
            try:
                data = r.json()
            except ValueError:
                # Not JSON — might be HTML bot-challenge
                log.debug(f"  HB API: non-JSON response from {ep}")
                continue

            price  = _deep_find_price(data, weight)
            seller = _deep_find_seller(data)

            if price:
                log.info(f"  ✅ HB API price: {price:,.2f} TRY  seller: {seller or '(unknown)'}")
                return price, seller

            log.debug(f"  HB API {ep[:60]}: no sane price found in JSON")
        except Exception as exc:
            log.debug(f"  HB API {ep[:60]} error: {exc}")

    log.warning("  ⚠ HB API: all endpoints failed to return a price")
    return None, ""


def fetch_live_gold_price_try() -> Optional[float]:
    """
    Fetch today's live gram-gold price (24-ayar) from bigpara.hurriyet.com.tr
    and return the 22-ayar equivalent (×0.916).
    Returns None if the fetch fails for any reason.
    """
    if not REQUESTS_OK:
        return None
    try:
        headers = {"User-Agent": USER_AGENTS[0], "Accept-Language": "tr-TR,tr;q=0.9"}
        r = _requests.get(
            "https://bigpara.hurriyet.com.tr/altin/gram-altin-fiyati/",
            headers=headers, timeout=10,
        )
        r.raise_for_status()
        # bigpara renders price as e.g. "7.126,33" inside a span
        m = re.search(
            r'(?:gram[- ]alt[iı]n|GAU)[^<]{0,200}?([\d]{1,2}\.[\d]{3},[\d]{2})',
            r.text, re.I | re.S,
        )
        if not m:
            # Broader fallback: any 4-5 digit number with Turkish format ~5000-15000
            m = re.search(r'\b([5-9]\.\d{3},\d{2}|1[0-5]\.\d{3},\d{2})\b', r.text)
        if m:
            price_24k = parse_try_price(m.group(1))
            if price_24k and 4_000 < price_24k < 20_000:
                price_22k = round(price_24k * 0.916, 2)
                log.info(f"  📈 Live gold: {fmt_price(price_24k)}/g (24k) → "
                         f"{fmt_price(price_22k)}/g (22k)")
                return price_22k
    except Exception as e:
        log.debug(f"Gold price fetch failed: {e}")
    return None


def _oos(html: str) -> bool:
    """
    Out-of-stock detector — covers Turkish & English phrases used by
    Hepsiburada, Amazon TR, N11, and Idefix.
    """
    return bool(re.search(
        r"tükendi"
        r"|stokta\s*yok"
        r"|stok\s*yok"
        r"|out[\s\-]of[\s\-]stock"
        r"|satışa\s*kapalı"
        r"|sold[\s\-]out"
        r"|şu\s*anda\s*mevcut\s*değil"       # Amazon TR: "Şu anda mevcut değil"
        r"|currently\s*unavailable"
        r"|bu\s*ürünü?\s*satın\s*alamazsınız"
        r"|ürün\s*mevcut\s*değil"
        r"|satışta\s*değil"
        r"|temin\s*edilemiyor",
        html, re.I,
    ))


def _h1(html: str) -> str:
    mm = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
    if mm:
        return re.sub(r"<[^>]+>", "", mm.group(1)).strip()
    return "Unknown"


# ── Hepsiburada ───────────────────────────────────────────────────────────────
def parse_hepsiburada(html: str, url: str, weight: str,
                      js_data: Optional[dict] = None) -> Product:
    site = "Hepsiburada"
    name = _h1(html)
    js_data = js_data or {}

    if _oos(html):
        return Product(site=site, name=name, weight=weight, price=None,
                       url=url, status="out_of_stock")

    price:  Optional[float] = None
    seller: str             = js_data.get("seller") or ""

    # ── Priority 1: "Sepete Özel Fiyat" from JS (discountedPrice) ────────────
    # This is the cart-exclusive lower price HB sometimes hides below the list price.
    cart_price = js_data.get("cartPrice")
    if cart_price:
        price = sanity_check(cart_price, weight)
        if price:
            log.debug(f"  HB sepete özel (JS cartPrice): {price}")

    # ── Priority 2: Regular JS price ─────────────────────────────────────────
    if not price and js_data.get("price"):
        price = sanity_check(js_data["price"], weight)

    # ── Priority 3: HTML — vicinity scan after "checkout-price" marker ──────────
    # The nested-div structure makes (.*?)</div> unreliable.
    # Instead: find the marker, then scan the next 800 chars for all price numbers,
    # and take the LOWEST one (the discounted cart price is always cheaper).
    if not price:
        mm = re.search(r'data-test-id="checkout-price"', html, re.I)
        if mm:
            vicinity = html[mm.start(): mm.start() + 800]
            # Strip tags, find all Turkish-format prices
            clean = re.sub(r'<[^>]+>', ' ', vicinity)
            candidates = []
            for pm in re.finditer(
                r'([\d]{2,3}[.,][\d]{3}(?:[.,][\d]{1,2})?)',
                clean,
            ):
                v = parse_try_price(pm.group(1))
                if v and v > 1000:
                    candidates.append(v)
            if candidates:
                # Smallest value in block = discounted cart price
                price = sanity_check(min(candidates), weight)

    # ── Priority 3b: Targeted label → next-sibling div pattern ──────────────
    # From actual HB HTML:
    #   <span ...>Sepete özel fiyat</span></div>
    #   <div ...>74.121,69 TL</div>
    # The price div IMMEDIATELY follows the label-container closing tag.
    if not price:
        mm = re.search(
            r'[Ss]epete\s+[öo]zel\s+fiyat\s*</span>\s*</div>\s*'
            r'<div[^>]*>\s*([\d]{1,3}(?:[.,]\d{3})+(?:[.,]\d{0,2})?)\s*(?:TL|₺)',
            html, re.I,
        )
        if mm:
            price = sanity_check(parse_try_price(mm.group(1)), weight)

    # ── Priority 3c: "Sepette İndirim" label vicinity ────────────────────────
    if not price:
        for label_pat in [
            r'[Ss]epete?\s*[Öö]zel\s*[Ff]iyat',
            r'[Ss]epette\s*[İi]ndirim',
        ]:
            mm = re.search(label_pat, html, re.I)
            if mm:
                vicinity = html[mm.start(): mm.start() + 500]
                clean = re.sub(r'<[^>]+>', ' ', vicinity)
                candidates = []
                for pm in re.finditer(r'([\d]{2,3}[.,][\d]{3}(?:[.,][\d]{1,2})?)', clean):
                    v = parse_try_price(pm.group(1))
                    if v and v > 1000:
                        candidates.append(v)
                if candidates:
                    price = sanity_check(min(candidates), weight)
                    if price:
                        break

    # ── Priority 4: window.__PRODUCT_DETAIL_APP__ JSON in page source ─────────
    if not price:
        mm = re.search(
            r'window\.__PRODUCT_DETAIL_APP__\s*=\s*(\{.*?\})\s*;',
            html, re.S,
        )
        if mm:
            try:
                data = json.loads(mm.group(1))
                listing = None
                try:
                    listing = data["product"]["listings"][0]
                except (KeyError, IndexError, TypeError):
                    pass
                if listing:
                    pi = listing.get("priceInfo", {})
                    # Try discountedPrice (cart price) first
                    for key in ("discountedPrice", "cartPrice", "price"):
                        raw = pi.get(key)
                        if raw:
                            price = sanity_check(parse_try_price(str(raw)), weight)
                            if price:
                                break
                    if not seller:
                        seller = (listing.get("merchantName")
                                  or listing.get("sellerDisplayName")
                                  or "")
                if not price:
                    raw = data.get("product", {}).get("price")
                    if raw:
                        price = sanity_check(parse_try_price(str(raw)), weight)
            except Exception:
                pass

    # ── Priority 5: seller name from HTML if still missing ────────────────────
    if not seller:
        for pat in [
            # data-hbus attribute: HTML-encoded JSON — e.g. &quot;merchant_name&quot;:&quot;AHLATCI&quot;
            # This is the MOST RELIABLE source — comes from HB's own tracking JSON
            r'&quot;merchant_name&quot;:&quot;([A-Z0-9ÇŞİÖÜa-zçşıöü_\- ]{2,60})&quot;',
            r'data-test-id="merchant-name"[^>]*>\s*([^<]{2,60})',   # HB stable id
            r'"merchant_name"\s*:\s*"([^"]{2,60})"',                # GTM dataLayer (snake_case)
            r'"merchantName"\s*:\s*"([^"]{2,60})"',
            r'"sellerDisplayName"\s*:\s*"([^"]{2,60})"',
            r'data-merchantname="([^"]{2,60})"',
            r'[Ss]at[iı]c[iı]\s*[:\s]{0,3}<[^>]+>\s*([A-ZÇŞİÖÜa-zçşıöü][^<]{1,50})',
            r'class="[^"]*merchant[^"]*name[^"]*"[^>]*>\s*([^<]{2,60})',
        ]:
            mm = re.search(pat, html, re.I)
            if mm:
                seller = mm.group(1).strip()
                if seller:
                    break

    # ── Priority 6: Knockout / data-test-id / itemprop rendered spans ─────────
    if not price:
        # Vicinity scan around data-test-id="price" — take LARGEST (regular list price)
        mm = re.search(r'data-test-id="price"', html, re.I)
        if mm:
            vicinity = html[mm.start(): mm.start() + 600]
            clean = re.sub(r'<[^>]+>', ' ', vicinity)
            candidates = []
            for pm in re.finditer(r'([\d]{2,3}[.,][\d]{3}(?:[.,][\d]{1,2})?)', clean):
                v = parse_try_price(pm.group(1))
                if v and v > 1000:
                    candidates.append(v)
            if candidates:
                price = sanity_check(max(candidates), weight)

    if not price:
        for pat in [
            r'data-bind="[^"]*markupText[^"]*displayedPriceValue[^"]*"[^>]*>\s*([\d.,\s₺TL]+)',
            r'class="[^"]*price-value[^"]*"[^>]*>\s*([\d.,\s₺TL]+)',
            r'class="[^"]*currentPrice[^"]*"[^>]*>\s*([\d.,\s₺TL]+)',
            r'itemprop="price"[^>]*content="([^"]+)"',
        ]:
            mm = re.search(pat, html, re.I)
            if mm:
                price = sanity_check(parse_try_price(mm.group(1).strip()), weight)
                if price:
                    break

    # ── Priority 7: JSON-LD / meta ────────────────────────────────────────────
    if not price:
        price = sanity_check(_json_ld_price(html), weight) or \
                sanity_check(_meta_price(html), weight)

    if price is None:
        return Product(site=site, name=name, weight=weight, price=None,
                       url=url, status="price_not_found", seller=seller)
    return Product(site=site, name=name, weight=weight, price=price,
                   url=url, seller=seller)


# ── Amazon Turkey ─────────────────────────────────────────────────────────────
def parse_amazon(html: str, url: str, weight: str) -> Product:
    site = "Amazon TR"
    name = _h1(html)

    # OOS detection for Amazon — use positive signals first.
    # "Sepete Ekle" / "add-to-cart-button" is the most reliable in-stock signal.
    # Only fall back to text scanning if no buy button is found at all.
    has_cart_btn = bool(re.search(
        r'id="add-to-cart-button"|id="buy-now-button"|name="submit\.add-to-cart"'
        r'|buyingPrice|id="buybox"',
        html, re.I,
    ))
    if not has_cart_btn:
        # No buy button → check for OOS phrases scoped to first ~15 KB
        # (avoids picking up "mevcut değil" from recommended products section)
        oos_scope = html[:15000]
        if _oos(oos_scope):
            log.debug("  Amazon: no buy-button + OOS phrase found → out_of_stock")
            return Product(site=site, name=name, weight=weight, price=None,
                           url=url, status="out_of_stock")
    else:
        log.debug("  Amazon: buy-button present → treating as in-stock")

    price: Optional[float] = None

    # ── Strategy 1: isolate the main price block first, then search inside it ──
    # Amazon has multiple a-price elements (strikethrough, instalment, etc.)
    # The real price lives inside #corePriceDisplay_desktop_feature_div
    # Use a wide positional slice instead of fragile regex to avoid cutting off too early.
    m_start = re.search(r'id="corePriceDisplay_desktop_feature_div"', html, re.I)
    search_scope = html[m_start.start(): m_start.start() + 4000] if m_start else html

    # Within that block, grab a-price-whole + a-price-fraction
    m_whole = re.search(r'class="a-price-whole"[^>]*>([\d.,]+)', search_scope, re.I)
    m_frac  = re.search(r'class="a-price-fraction"[^>]*>([\d]+)',  search_scope, re.I)
    if m_whole:
        raw = m_whole.group(1).rstrip(".,")
        if m_frac:
            raw += "," + m_frac.group(1)
        price = sanity_check(parse_try_price(raw), weight)

    # ── Strategy 2: legacy price block IDs ────────────────────────────────────
    if not price:
        for pat in [
            r'id="priceblock_ourprice"[^>]*>\s*([\d.,\s₺TL]+)',
            r'id="priceblock_dealprice"[^>]*>\s*([\d.,\s₺TL]+)',
            r'itemprop="price"\s+content="([^"]+)"',
        ]:
            mm = re.search(pat, html, re.I)
            if mm:
                price = sanity_check(parse_try_price(mm.group(1).strip()), weight)
                if price:
                    break

    # ── Strategy 3: JSON-LD / meta ─────────────────────────────────────────────
    if not price:
        price = sanity_check(_json_ld_price(html), weight) or \
                sanity_check(_meta_price(html), weight)

    # ── Strategy 4: scan ALL a-price-whole occurrences, take first sane one ───
    if not price:
        for mm in re.finditer(r'class="a-price-whole"[^>]*>([\d.,]+)', html, re.I):
            candidate = sanity_check(parse_try_price(mm.group(1).rstrip(".,")), weight)
            if candidate:
                price = candidate
                break

    # ── Strategy 5: a-offscreen span — Amazon's accessible price text ─────────
    # e.g. <span class="a-offscreen">₺74.476,53</span>
    # This is the most reliable Amazon price signal — used for screen readers.
    if not price:
        for mm in re.finditer(
            r'class="a-offscreen"[^>]*>\s*[₺TL]?\s*([\d]{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?)',
            html, re.I,
        ):
            candidate = sanity_check(parse_try_price(mm.group(1)), weight)
            if candidate:
                price = candidate
                log.debug(f"  Amazon: price from a-offscreen: {price}")
                break

    # ── Strategy 6: swatchPrice / twister JSON data ────────────────────────────
    # Amazon embeds selected variation price in a JSON blob
    if not price:
        for mm in re.finditer(
            r'"displayPrice"\s*:\s*"[₺TL]?\s*([\d]{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?)"',
            html, re.I,
        ):
            candidate = sanity_check(parse_try_price(mm.group(1)), weight)
            if candidate:
                price = candidate
                log.debug(f"  Amazon: price from displayPrice JSON: {price}")
                break

    # ── Strategy 7: priceValue / basisPrice in data-a-* attributes ────────────
    if not price:
        for pat7 in [
            r'data-a-color="price"[^>]*>\s*<[^>]+class="[^"]*a-offscreen[^"]*"[^>]*>\s*[₺TL]?\s*([\d.,]+)',
            r'"priceValue"\s*:\s*["\']?([\d.,]+)',
            r'data-csa-c-item-price="([^"]+)"',
        ]:
            mm = re.search(pat7, html, re.I)
            if mm:
                candidate = sanity_check(parse_try_price(mm.group(1)), weight)
                if candidate:
                    price = candidate
                    log.debug(f"  Amazon: price from strategy-7: {price}")
                    break

    # ── Diagnostic: log what was / wasn't found in the page ───────────────────
    is_captcha  = bool(re.search(r'robot_check|Type the characters|captcha', html, re.I))
    has_buybox  = 'id="buybox"' in html or 'id="add-to-cart-button"' in html
    has_offscr  = 'a-offscreen' in html
    has_core    = 'corePriceDisplay' in html
    log.info(
        f"  🔎 Amazon HTML — captcha={'⚠' if is_captcha else '✗'}  "
        f"buybox={'✓' if has_buybox else '✗'}  "
        f"a-offscreen={'✓' if has_offscr else '✗'}  "
        f"corePrice={'✓' if has_core else '✗'}  "
        f"size={len(html):,}b  price={'✓ ' + str(round(price)) if price else '✗ NOT FOUND'}"
    )

    # ── Debug HTML dump (env-controlled) ──────────────────────────────────────
    if price is None and os.environ.get("GOLD_DEBUG_HTML"):
        try:
            import hashlib, textwrap
            slug = hashlib.md5(url.encode()).hexdigest()[:8]
            dbg_path = f"debug_amazon_{slug}.html"
            with open(dbg_path, "w", encoding="utf-8") as fh:
                fh.write(html)
            log.info(f"  💾 Debug HTML saved → {dbg_path}")
        except Exception:
            pass

    # ── Seller / merchant name ─────────────────────────────────────────────────
    seller = _extract_seller_html(html, [
        # Sold-by link text (most reliable on Amazon)
        r'id="sellerProfileTriggerId"[^>]*>\s*([^<]{2,60})',
        r'id="merchant-info"[^>]*>[^<]*?by\s+([^<]{2,60}?)(?:\s*<|\s*\.)',
        # JSON fragments in page source
        r'"merchantName"\s*:\s*"([^"]{2,60})"',
        r'"sellerDisplayName"\s*:\s*"([^"]{2,60})"',
        r'"soldByThirdParty"\s*:\s*"([^"]{2,60})"',
        # "Satıcı:" label (Turkish Amazon)
        r'[Ss]at[iı]c[iı]\s*[:\s]{1,3}<[^>]+>\s*([^<]{2,60})',
        r'"brand"\s*:\s*"([^"]{2,60})"',
    ])

    if price is None:
        return Product(site=site, name=name, weight=weight, price=None,
                       url=url, status="price_not_found", seller=seller)
    return Product(site=site, name=name, weight=weight, price=price,
                   url=url, seller=seller)


def _extract_seller_html(html: str, patterns: List[str]) -> str:
    """Try each regex pattern in order, return first non-empty match."""
    for pat in patterns:
        mm = re.search(pat, html, re.I)
        if mm:
            val = mm.group(1).strip()
            if val:
                return val
    return ""


# ── N11 ───────────────────────────────────────────────────────────────────────
def parse_n11(html: str, url: str, weight: str) -> Product:
    site = "N11"
    name = _h1(html)

    if _oos(html):
        return Product(site=site, name=name, weight=weight, price=None,
                       url=url, status="out_of_stock")

    price: Optional[float] = None
    for pat in [
        r'class="[^"]*newPrice[^"]*"[^>]*>\s*<[^>]+>\s*([\d.,\s₺TL]+)',
        r'class="[^"]*price[^"]*"[^>]*>\s*([\d.,\s₺TL]+)',
        r'itemprop="price"\s+content="([^"]+)"',
        r'"price":\s*"?([\d.,]+)"?',
    ]:
        mm = re.search(pat, html, re.I)
        if mm:
            price = sanity_check(parse_try_price(mm.group(1).strip()), weight)
            if price:
                break

    if not price:
        price = sanity_check(_json_ld_price(html), weight) or \
                sanity_check(_meta_price(html), weight)

    seller = _extract_seller_html(html, [
        r'"sellerName"\s*:\s*"([^"]{2,60})"',
        r'"merchantName"\s*:\s*"([^"]{2,60})"',
        r'class="[^"]*seller[^"]*name[^"]*"[^>]*>\s*([^<]{2,60})',
        r'[Ss]atıcı[:\s]{1,5}<[^>]+>([^<]{2,60})',
    ])

    if price is None:
        return Product(site=site, name=name, weight=weight, price=None,
                       url=url, status="price_not_found", seller=seller)
    return Product(site=site, name=name, weight=weight, price=price,
                   url=url, seller=seller)


# ── Idefix ────────────────────────────────────────────────────────────────────
def parse_idefix(html: str, url: str, weight: str) -> Product:
    site = "Idefix"
    name = _h1(html)

    if _oos(html):
        return Product(site=site, name=name, weight=weight, price=None,
                       url=url, status="out_of_stock")

    price: Optional[float] = None
    for pat in [
        r'class="[^"]*(?:price|fiyat|amount)[^"]*"[^>]*>\s*([\d.,\s₺TL]+)',
        r'itemprop="price"\s+content="([^"]+)"',
    ]:
        mm = re.search(pat, html, re.I)
        if mm:
            price = sanity_check(parse_try_price(mm.group(1).strip()), weight)
            if price:
                break

    if not price:
        price = sanity_check(_json_ld_price(html), weight) or \
                sanity_check(_meta_price(html), weight)

    seller = _extract_seller_html(html, [
        # Idefix: <a href="/satici/SELLER-SLUG">SELLER NAME</a>
        r'<a[^>]+href="/satici/[^"]*"[^>]*>\s*([^<]{2,60})',
        r'"brand"\s*:\s*"([^"]{2,60})"',
        r'"sellerName"\s*:\s*"([^"]{2,60})"',
        r'class="[^"]*(?:brand|seller|merchant)[^"]*"[^>]*>\s*([^<]{2,60})',
        r'itemprop="brand"[^>]*>\s*<[^>]+>\s*([^<]{2,60})',
    ])

    if price is None:
        return Product(site=site, name=name, weight=weight, price=None,
                       url=url, status="price_not_found", seller=seller)
    return Product(site=site, name=name, weight=weight, price=price,
                   url=url, seller=seller)


# ── Generic fallback ──────────────────────────────────────────────────────────
def parse_generic(html: str, url: str, weight: str) -> Product:
    site = site_from_url(url)
    name = _h1(html)

    if _oos(html):
        return Product(site=site, name=name, weight=weight, price=None,
                       url=url, status="out_of_stock")

    price = sanity_check(_json_ld_price(html), weight) or \
            sanity_check(_meta_price(html), weight)
    if not price:
        mm = re.search(
            r'class="[^"]*(?:price|fiyat|amount|tutar)[^"]*"[^>]*>\s*([\d.,\s₺TL]+)',
            html, re.I,
        )
        if mm:
            price = sanity_check(parse_try_price(mm.group(1).strip()), weight)

    if price is None:
        return Product(site=site, name=name, weight=weight, price=None,
                       url=url, status="price_not_found")
    return Product(site=site, name=name, weight=weight, price=price, url=url)


# ══════════════════════════════════════════════════════════════════════════════
#  PLAYWRIGHT SCRAPING ENGINE
# ══════════════════════════════════════════════════════════════════════════════

async def _new_context(browser: Browser, block_assets: bool = True) -> BrowserContext:
    """Create a fresh browser context with a random User-Agent."""
    ua = random.choice(USER_AGENTS)
    ctx = await browser.new_context(
        user_agent=ua,
        viewport={"width": random.randint(1280, 1920), "height": random.randint(800, 1080)},
        locale="tr-TR",
        timezone_id="Europe/Istanbul",
        extra_http_headers={
            "Accept-Language":           "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept":                    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest":            "document",
            "Sec-Fetch-Mode":            "navigate",
            "Sec-Fetch-Site":            "none",
        },
    )
    await ctx.add_init_script("""
        // ── Hide all headless / automation signals ────────────────────────────
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        delete navigator.__proto__.webdriver;

        // Realistic chrome object
        window.chrome = {
            runtime: { onMessage: { addListener: ()=>{} }, id: undefined },
            loadTimes: function(){ return {}; },
            csi:        function(){ return {}; },
            app:        { isInstalled: false },
        };

        // Realistic plugins list (3 common ones)
        Object.defineProperty(navigator, 'plugins', { get: () => {
            var mimeTypes = { length: 0 };
            var plugins = [
                { name:'Chrome PDF Plugin',  filename:'internal-pdf-viewer',    description:'Portable Document Format', length:1, 0:{type:'application/x-google-chrome-pdf'} },
                { name:'Chrome PDF Viewer',  filename:'mhjfbmdgcfjbbpaeojofohoefgiehjai', description:'',                  length:1, 0:{type:'application/pdf'} },
                { name:'Native Client',      filename:'internal-nacl-plugin',   description:'',                          length:2, 0:{type:'application/x-nacl'}, 1:{type:'application/x-pnacl'} },
            ];
            plugins.length = 3;
            plugins.item = function(i){ return plugins[i]; };
            plugins.namedItem = function(n){ return plugins.find(p=>p.name===n)||null; };
            plugins.refresh = function(){};
            return plugins;
        }});

        Object.defineProperty(navigator, 'languages',          { get: () => ['tr-TR','tr','en-US','en'] });
        Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
        Object.defineProperty(navigator, 'deviceMemory',        { get: () => 8 });
        Object.defineProperty(navigator, 'maxTouchPoints',      { get: () => 0 });
        Object.defineProperty(screen,    'colorDepth',          { get: () => 24 });
        Object.defineProperty(screen,    'pixelDepth',          { get: () => 24 });

        // Spoof permissions to avoid automation detection
        const _origPerms = window.navigator.permissions.query.bind(navigator.permissions);
        window.navigator.permissions.query = (p) =>
            p.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : _origPerms(p);
    """)
    return ctx


# ── Single combined JS extractor for Hepsiburada ─────────────────────────────
# Returns a JSON string: {"price": "74057.00", "cartPrice": "74057.00", "seller": "Ahlatcı"}
# cartPrice = "sepete özel fiyat" (cart-exclusive discounted price) — use if available
_HB_JS_COMBINED = """
(function(){
    var result = {price: null, cartPrice: null, seller: null};

    // Helper: walk all leaf text nodes inside an element, collect price-like strings
    function leafPrices(root) {
        var found = [];
        try {
            var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
            while (walker.nextNode()) {
                var t = walker.currentNode.textContent.replace(/\\s+/g, ' ').trim();
                // match Turkish price: 74.121,69 or 74121,69 or 74.121
                if (/\\d{2,3}\\.\\d{3}[,.]\\d{0,2}/.test(t) || /\\d{5,}/.test(t)) {
                    found.push(t);
                }
            }
        } catch(e) {}
        return found;
    }

    try {
        // ── 1. data-test-id="checkout-price"  →  sepete özel fiyat ───────────
        // Use TreeWalker to get only leaf text nodes (avoids mixing regular + cart prices)
        var checkoutEl = document.querySelector('[data-test-id="checkout-price"]');
        if (checkoutEl) {
            var leafs = leafPrices(checkoutEl);
            if (leafs.length > 0) {
                // The cart/discount price is always the SMALLEST number in this block
                var nums = [];
                leafs.forEach(function(t) {
                    var n = parseFloat(t.replace(/\\./g,'').replace(',','.'));
                    if (!isNaN(n) && n > 1000) nums.push(n);
                });
                if (nums.length > 0) result.cartPrice = String(Math.min.apply(null, nums));
            }
            // Fallback: raw innerText
            if (!result.cartPrice) result.cartPrice = checkoutEl.innerText || '';
        }

        // ── 2. data-test-id="price" → regular list price ──────────────────────
        var priceBlockEl = document.querySelector('[data-test-id="price"]');
        if (priceBlockEl) {
            var leafs2 = leafPrices(priceBlockEl);
            var nums2 = [];
            leafs2.forEach(function(t) {
                var n = parseFloat(t.replace(/\\./g,'').replace(',','.'));
                if (!isNaN(n) && n > 1000) nums2.push(n);
            });
            // Regular list price is the LARGEST number in the price block
            if (nums2.length > 0) result.price = String(Math.max.apply(null, nums2));
            if (!result.price) result.price = priceBlockEl.innerText || '';
        }

        // ── 3. window.__PRODUCT_DETAIL_APP__ (JS bundle) ──────────────────────
        var d = window.__PRODUCT_DETAIL_APP__;
        if (d) {
            var listing = (d.product && d.product.listings && d.product.listings[0]) || null;
            if (listing) {
                var pi = listing.priceInfo || {};
                if (!result.cartPrice) {
                    var dp = pi.discountedPrice || pi.cartPrice || pi.price || '';
                    if (dp) result.cartPrice = String(dp);
                }
                if (!result.price) {
                    if (pi.price) result.price = String(pi.price);
                }
                result.seller = listing.merchantName
                             || listing.merchant_name
                             || listing.sellerDisplayName
                             || listing.merchantSeoName
                             || null;
            }
            if (!result.price && d.product && d.product.price) {
                result.price = String(d.product.price);
            }
        }

        // ── 4. window.dataLayer — GTM has merchant_name ───────────────────────
        if (!result.seller && window.dataLayer) {
            for (var i = 0; i < window.dataLayer.length; i++) {
                var layer = window.dataLayer[i];
                var mn = (layer && (layer.merchant_name
                       || (layer.ecommerce && layer.ecommerce.merchant_name)));
                if (mn) { result.seller = mn; break; }
                try {
                    var prod = layer.ecommerce.detail.products[0]
                            || layer.ecommerce.impressions[0];
                    if (prod && prod.merchant_name) { result.seller = prod.merchant_name; break; }
                } catch(e2) {}
            }
        }

        // ── 5. DOM fallback: knockout / generic price span ────────────────────
        if (!result.price) {
            var fbEl = document.querySelector('[data-bind*="displayedPriceValue"]')
                    || document.querySelector('[class*="price-value"]')
                    || document.querySelector('[class*="currentPrice"]');
            if (fbEl) result.price = fbEl.innerText;
        }

        // ── 6. data-hbus attribute — HB embeds merchant_name as JSON ─────────
        // This is the most reliable source: &quot;merchant_name&quot;:&quot;AHLATCI&quot;
        if (!result.seller) {
            try {
                var hbusEl = document.querySelector('[data-hbus*="merchant_name"]');
                if (hbusEl) {
                    var hbusData = JSON.parse(hbusEl.getAttribute('data-hbus'));
                    result.seller = (hbusData.data && hbusData.data.merchant_name) || null;
                }
            } catch(e3) {}
        }

        // ── 7. Seller from DOM fallback ───────────────────────────────────────
        if (!result.seller) {
            var selEl = document.querySelector('[data-test-id="merchant-name"]')
                     || document.querySelector('[class*="merchant-name"]')
                     || document.querySelector('[data-merchantname]')
                     || document.querySelector('[class*="seller-name"]');
            if (selEl) {
                result.seller = (selEl.getAttribute('data-merchantname')
                              || selEl.innerText || '').trim();
            }
        }

    } catch(e) {}
    return JSON.stringify(result);
})()
"""


async def fetch_page_pw(browser: Browser, url: str) -> Tuple[Optional[str], Optional[dict]]:
    """
    Fetch a page with Playwright.
    Returns (html_string, js_data).
    js_data is a dict {"price": float|None, "cartPrice": float|None, "seller": str|None}
    populated only for Hepsiburada via page.evaluate().
    """
    domain = urlparse(url).netloc.lower()
    is_hb  = "hepsiburada.com" in domain

    ctx = await _new_context(browser, block_assets=not is_hb)
    page: Optional[Page] = None
    js_data: dict = {"price": None, "cartPrice": None, "seller": None}

    try:
        page = await ctx.new_page()

        if not is_hb:
            async def _blocker(route):
                if route.request.resource_type in ("image", "font", "media", "stylesheet"):
                    await route.abort()
                else:
                    await route.continue_()
            await page.route("**/*", _blocker)

        await page.goto(url, timeout=PAGE_TIMEOUT, wait_until="domcontentloaded")

        # ── Hepsiburada: wait → networkidle → scroll → JS extractor ─────────
        if is_hb:
            # Step 1: simulate human-like mouse movement before page interacts
            await page.mouse.move(
                random.randint(300, 700), random.randint(100, 300)
            )
            await asyncio.sleep(random.uniform(0.3, 0.7))
            await page.mouse.move(
                random.randint(500, 900), random.randint(300, 600)
            )
            await asyncio.sleep(random.uniform(0.2, 0.5))

            # Step 2: wait until actual price DATA is available in the DOM/JS bundle
            # wait_for_function is more reliable than wait_for_selector because it
            # checks that __PRODUCT_DETAIL_APP__ has real listing data, not just
            # that a DOM element exists (which can happen on bot-challenge pages too).
            try:
                await page.wait_for_function(
                    """() => {
                        // Option A: checkout-price element has visible text
                        var cp = document.querySelector('[data-test-id="checkout-price"]');
                        if (cp && cp.innerText && cp.innerText.trim().length > 3) return true;
                        // Option B: price element has visible text
                        var pp = document.querySelector('[data-test-id="price"]');
                        if (pp && pp.innerText && pp.innerText.trim().length > 3) return true;
                        // Option C: JS bundle has listing price data
                        var d = window.__PRODUCT_DETAIL_APP__;
                        if (d && d.product && d.product.listings &&
                            d.product.listings[0] && d.product.listings[0].priceInfo) return true;
                        return false;
                    }""",
                    timeout=22_000,
                )
                log.info("  ✓ HB: price data confirmed in DOM/JS")
            except PWTimeout:
                log.warning("  ⚠ HB: wait_for_function timeout — may be bot-blocked")

            # Step 3: brief additional settle time for React/Knockout hydration
            try:
                await page.wait_for_load_state("networkidle", timeout=10_000)
            except PWTimeout:
                pass

            # Step 4: scroll to trigger lazy-render, then wait
            await page.evaluate("window.scrollBy(0, 400)")
            await asyncio.sleep(1.5)
            await page.evaluate("window.scrollBy(0, 400)")
            await asyncio.sleep(2.5)   # give Knockout / React hydration time

            # Step 5: run combined JS extractor
            async def _run_hb_js() -> None:
                try:
                    raw = await page.evaluate(_HB_JS_COMBINED)
                    if raw:
                        parsed = json.loads(raw)
                        for key in ("cartPrice", "price"):
                            val = parse_try_price(str(parsed.get(key) or ""))
                            if val and val > 1000:
                                js_data[key] = val
                                log.info(f"  🟠 HB JS {key}: {val:,.2f}")
                        seller_raw = (parsed.get("seller") or "").strip()
                        if seller_raw:
                            js_data["seller"] = seller_raw
                            log.info(f"  🟠 HB JS seller: {seller_raw}")
                except Exception as e:
                    log.warning(f"  ⚠ HB JS extractor error: {e}")

            await _run_hb_js()

            # Step 6: if no price yet, scroll to bottom then top, wait, retry
            if not any(js_data.get(k) for k in ("cartPrice", "price")):
                log.info("  🔄 HB: no price on first pass — extra scroll + retry…")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
                await asyncio.sleep(2.0)
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(1.5)
                await _run_hb_js()

            if not any(js_data.get(k) for k in ("cartPrice", "price")):
                log.warning("  ⚠ HB JS: no price found — possibly bot-blocked or captcha")

        else:
            try:
                await page.wait_for_load_state("networkidle", timeout=8_000)
            except PWTimeout:
                pass
            await page.evaluate("window.scrollBy(0, window.innerHeight * 0.4)")
            await asyncio.sleep(random.uniform(0.5, 1.2))

        html = await page.content()

        # ── Diagnostics for Hepsiburada (INFO level so always visible) ────────
        if is_hb:
            has_checkout  = 'data-test-id="checkout-price"' in html
            has_sepete    = bool(re.search(r'[Ss]epete\s+[öo]zel\s+fiyat', html))
            has_hbus      = 'data-hbus' in html
            has_prod_app  = '__PRODUCT_DETAIL_APP__' in html
            log.info(
                f"  🔎 HB HTML check — "
                f"checkout-price={'✓' if has_checkout else '✗'}  "
                f"sepete-özel={'✓' if has_sepete else '✗'}  "
                f"data-hbus={'✓' if has_hbus else '✗'}  "
                f"PRODUCT_APP={'✓' if has_prod_app else '✗'}  "
                f"size={len(html):,}b"
            )
            if not has_checkout and not has_sepete:
                log.warning("  ⚠ HB: price markers absent — bot-block or captcha page?")

        return html, js_data

    except PWTimeout:
        log.warning(f"  ⚠ Timeout loading {url}")
        return None, js_data
    except Exception as exc:
        log.error(f"  ✗ Playwright error on {url}: {exc}")
        return None, js_data
    finally:
        if page:
            await page.close()
        await ctx.close()


async def scrape_all(url_map: Dict[str, List[dict]]) -> List[Product]:
    if not PW_OK:
        log.error("Playwright not installed. Run: pip3 install playwright && python3 -m playwright install chromium")
        return []

    tasks: List[tuple] = []
    for weight, entries in url_map.items():
        for entry in entries:
            tasks.append((weight, entry["url"], entry.get("site") or site_from_url(entry["url"])))

    if not tasks:
        log.warning("No product URLs configured.")
        return []

    results: List[Product] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-extensions",
            ],
        )
        log.info(f"Browser launched (headless={HEADLESS}). Scraping {len(tasks)} URL(s) …\n")

        for idx, (weight, url, site) in enumerate(tasks, 1):
            log.info(f"[{idx}/{len(tasks)}] [{weight}] {site} → {truncate(url, 70)}")

            html, js_data = await fetch_page_pw(browser, url)

            if html is None:
                product = Product(site=site, name="N/A", weight=weight, price=None,
                                  url=url, status="error", error_msg="Page load failed")
            else:
                try:
                    domain = urlparse(url).netloc.lower()
                    if "hepsiburada.com" in domain:
                        product = parse_hepsiburada(html, url, weight, js_data=js_data)
                    elif "amazon.com.tr" in domain:
                        product = parse_amazon(html, url, weight)
                    elif "n11.com" in domain:
                        product = parse_n11(html, url, weight)
                    elif "idefix.com" in domain:
                        product = parse_idefix(html, url, weight)
                    else:
                        product = parse_generic(html, url, weight)
                except Exception as exc:
                    log.exception(f"  ✗ Parser exception: {exc}")
                    product = Product(site=site, name="N/A", weight=weight, price=None,
                                      url=url, status="error", error_msg=str(exc))

            # ── HB fallback cascade: API JSON → requests HTML ─────────────────
            if (product.status in ("price_not_found", "error")
                    and "hepsiburada.com" in urlparse(url).netloc.lower()):

                # Fallback 1: internal JSON API (fastest, least bot-detected)
                log.info("  🔄 HB: trying internal JSON API fallback…")
                api_price, api_seller = fetch_hb_api_price(url, weight)
                if api_price:
                    # Build a Product from the API result; keep name from Playwright if available
                    prev_name   = product.name if product.name not in ("N/A", "Unknown") else "Hepsiburada"
                    prev_seller = api_seller or product.seller or ""
                    product = Product(
                        site=site, name=prev_name, weight=weight,
                        price=api_price, url=url, seller=prev_seller,
                    )
                    log.info(f"  ✓ HB API fallback OK: {fmt_price(product.price)}")

                # Fallback 2: plain HTTP request for the HTML page
                if product.status in ("price_not_found", "error"):
                    log.info("  🔄 HB: trying requests HTML fallback…")
                    html_fb = fetch_hb_html_requests(url)
                    if html_fb:
                        try:
                            product = parse_hepsiburada(html_fb, url, weight, js_data={})
                            if product.status == "ok":
                                log.info(f"  ✓ HB requests fallback OK: {fmt_price(product.price)}")
                            else:
                                log.warning("  ⚠ HB requests fallback: price still not found")
                        except Exception as exc:
                            log.debug(f"  HB requests fallback parse error: {exc}")

            # ── Amazon fallback: requests HTML if Playwright got bot-blocked ──
            if (product.status in ("price_not_found", "error")
                    and "amazon.com.tr" in urlparse(url).netloc.lower()):
                log.info("  🔄 Amazon: Playwright failed → trying requests fallback…")
                html_az = fetch_amazon_requests(url)
                if html_az:
                    try:
                        product = parse_amazon(html_az, url, weight)
                        if product.status == "ok":
                            log.info(f"  ✓ Amazon requests fallback OK: {fmt_price(product.price)}")
                        else:
                            log.warning("  ⚠ Amazon requests fallback: price still not found")
                    except Exception as exc:
                        log.debug(f"  Amazon requests fallback parse error: {exc}")

            if product.status == "ok":
                log.info(f"  ✓ {fmt_price(product.price)}  ({fmt_price(product.price_pgr)}/g)")
            elif product.status == "out_of_stock":
                log.warning("  ⚠ Out of stock")
            else:
                log.warning(f"  ✗ {product.status.upper()} — {product.error_msg}")

            results.append(product)
            if idx < len(tasks):
                random_delay()

        await browser.close()

    return results


# ══════════════════════════════════════════════════════════════════════════════
#  COMPARISON & DISPLAY
# ══════════════════════════════════════════════════════════════════════════════

STATUS_LABEL = {
    "out_of_stock":    "OUT OF STOCK",
    "price_not_found": "PRICE N/A",
    "error":           "FETCH ERROR",
}

WEIGHT_ORDER = ["5g", "10g", "15g", "20g"]


def compare(products: List[Product]) -> None:
    """
    Print per-weight tables (no URL column — avoids tabulate truncation)
    then a Best Deals summary with clickable OSC-8 hyperlinks printed
    as a separate numbered list so the full URL is never cut.
    """
    best_deals: List[dict] = []
    sep = "═" * 100

    print()
    print(sep)
    print(f"  {'22 AYAR ALTIN BİLEZİK — Price Comparison':^96}")
    print(sep)

    for weight in WEIGHT_ORDER:
        group    = [p for p in products if p.weight == weight]
        if not group:
            continue

        # Only show products that are in-stock AND have a valid price
        ok_items  = [p for p in group if p.status == "ok" and p.price]
        oos_items = [p for p in group if p.status == "out_of_stock"]
        err_items = [p for p in group if p.status in ("price_not_found", "error")]

        grams = WEIGHT_GRAMS.get(weight, 0)
        best  = min(ok_items, key=lambda x: x.price, default=None)
        worst = max(ok_items, key=lambda x: x.price, default=None)

        print(f"\n  ⚖️   Weight: {weight}  ({grams}g · 22 ayar · 916‰ purity)")
        print("  " + "─" * 98)

        if not ok_items:
            print(f"  {C_RED}  No purchasable products found for {weight}.{C_RESET}")
            # Still log OOS/errors for transparency
            for p in oos_items:
                print(f"  ✗  {p.site}: OUT OF STOCK  — {truncate(p.url, 70)}")
            for p in err_items:
                print(f"  ✗  {p.site}: {p.status.upper()} — {p.error_msg[:60]}")
            continue

        rows = []
        for p in sorted(ok_items, key=lambda x: x.price or 0):
            is_best  = best  and p.price == best.price
            is_worst = worst and p.price == worst.price and not is_best

            note = (C_GREEN + "★ BEST DEAL" + C_RESET) if is_best else \
                   (C_RED   + "▲ HIGHEST"   + C_RESET) if is_worst else ""

            savings = ""
            if best and not is_best and p.price:
                diff    = p.price - best.price
                savings = f"  save {fmt_price(diff)}"

            color_on  = C_GREEN if is_best else ""
            color_off = C_RESET if is_best else ""
            rows.append([
                color_on + p.site   + color_off,
                truncate(p.name, 40),
                truncate(p.seller, 20) if p.seller else "—",
                color_on + fmt_price(p.price) + color_off,
                fmt_price(p.price_pgr) + "/g",
                note + savings,
            ])

        # ── Table — no URL column (kept outside tabulate to avoid truncation) ──
        headers = ["Site", "Product", "Seller", "Price (TRY)", "Per Gram", "Note"]
        if TABULATE_OK:
            table = tabulate(rows, headers=headers, tablefmt="rounded_outline")
            print("\n".join("  " + ln for ln in table.splitlines()))
        else:
            col_w = [14, 42, 22, 22, 16, 40]
            print("  " + "  ".join(h.ljust(w) for h, w in zip(headers, col_w)))
            print("  " + "─" * 98)
            for row in rows:
                print("  " + "  ".join(str(c).ljust(w) for c, w in zip(row, col_w)))

        # ── Skipped items summary (compact, below table) ──────────────────────
        skipped = len(oos_items) + len(err_items)
        if skipped:
            oos_names  = ", ".join(p.site for p in oos_items)
            err_names  = ", ".join(p.site for p in err_items)
            parts = []
            if oos_names:
                parts.append(f"out of stock: {oos_names}")
            if err_names:
                parts.append(f"price N/A: {err_names}")
            print(f"  {C_RED}  ↳ Skipped {skipped} listing(s) — {'; '.join(parts)}{C_RESET}")

        if best:
            print(f"\n  {C_YELLOW}→ Cheapest {weight}: {best.site}  "
                  f"{fmt_price(best.price)}  ({fmt_price(best.price_pgr)}/g){C_RESET}")
            if worst and best.site != worst.site and worst.price:
                diff = worst.price - best.price
                pct  = diff / worst.price * 100
                print(f"  {C_CYAN}  You save {fmt_price(diff)} ({pct:.1f}%) "
                      f"vs {worst.site}{C_RESET}")
            best_deals.append({
                "weight":    weight,
                "site":      best.site,
                "seller":    best.seller,
                "price":     best.price,
                "price_pgr": best.price_pgr,
                "currency":  best.currency,
                "url":       best.url,
            })

    # ══════════════════════════════════════════════════════════════════════════
    #  BEST DEALS SUMMARY — table WITHOUT URL, then links as a numbered list
    # ══════════════════════════════════════════════════════════════════════════
    if best_deals:
        print()
        print(sep)
        print(f"  {C_BOLD}{'✅  BEST DEALS SUMMARY':^96}{C_RESET}")
        print(sep)

        # ── Price table (no URL column) ───────────────────────────────────────
        summary_rows = [[
            b["weight"],
            b["site"],
            truncate(b["seller"], 20) if b.get("seller") else "—",
            fmt_price(b["price"],     b["currency"]),
            fmt_price(b["price_pgr"], b["currency"]) + "/g",
        ] for b in best_deals]

        s_headers = ["Weight", "Best Site", "Seller", "Lowest Price", "Per Gram"]
        if TABULATE_OK:
            table = tabulate(summary_rows, headers=s_headers, tablefmt="rounded_outline")
            print("\n".join("  " + ln for ln in table.splitlines()))
        else:
            col_w = [8, 16, 22, 22, 18]
            print("  " + "  ".join(h.ljust(w) for h, w in zip(s_headers, col_w)))
            print("  " + "─" * 68)
            for row in summary_rows:
                print("  " + "  ".join(str(c).ljust(w) for c, w in zip(row, col_w)))

        # ── Clickable links as a numbered list (never inside tabulate) ────────
        print()
        print(f"  {C_BOLD}🔗  Best-Deal Links  (Cmd+click to open in browser):{C_RESET}")
        print("  " + "─" * 98)
        for i, b in enumerate(best_deals, 1):
            pgr_str  = f"  ·  {fmt_price(b['price_pgr'], b['currency'])}/g" if b.get("price_pgr") else ""
            seller_str = f"  ·  {b['seller']}" if b.get("seller") else ""
            label    = f"[{b['weight']}] {b['site']}{seller_str} — {fmt_price(b['price'], b['currency'])}{pgr_str}"
            # Full URL passed as OSC-8 target; label shown as clickable text
            clickable = hyperlink(b["url"], b["url"])
            print(f"  {C_YELLOW}{i}. {label}{C_RESET}")
            print(f"     {clickable}")
            print()

        print(f"  {C_CYAN}ℹ  OSC-8 links work in iTerm2 · macOS Terminal 3.4+ · "
              f"Windows Terminal · VS Code{C_RESET}")

    print()
    print(sep)
    print()


# ══════════════════════════════════════════════════════════════════════════════
#  HTML OUTPUT
# ══════════════════════════════════════════════════════════════════════════════

def generate_html(products: List[Product], live_gold_price: Optional[float] = None) -> str:
    """Generate a self-contained HTML page with the price comparison results."""
    istanbul = timezone(timedelta(hours=3))
    now      = datetime.now(istanbul)
    ts       = now.strftime("%d %B %Y, %H:%M (Istanbul)")

    gold_info = (
        f'<span class="badge bg-warning text-dark fs-6 ms-2">'
        f'📈 22k: {fmt_price(live_gold_price)}/g</span>'
        if live_gold_price else ""
    )

    def _row_class(p: Product, best: Optional[Product], worst: Optional[Product]) -> str:
        if best and p.price == best.price:   return "table-success fw-bold"
        if worst and p.price == worst.price: return "table-danger"
        return ""

    def _note(p: Product, best: Optional[Product], worst: Optional[Product]) -> str:
        if best and p.price == best.price:   return "⭐ En Ucuz"
        if worst and p.price == worst.price: return "▲ En Pahalı"
        if best and p.price:
            diff = p.price - best.price
            return f"+{fmt_price(diff)}"
        return ""

    weight_sections = ""
    best_deals_rows = ""

    for weight in WEIGHT_ORDER:
        group     = [p for p in products if p.weight == weight]
        ok_items  = [p for p in group if p.status == "ok" and p.price]
        oos_items = [p for p in group if p.status == "out_of_stock"]
        err_items = [p for p in group if p.status in ("price_not_found", "error")]

        grams = WEIGHT_GRAMS.get(weight, 0)
        best  = min(ok_items, key=lambda x: x.price, default=None)
        worst = max(ok_items, key=lambda x: x.price, default=None)

        rows_html = ""
        for p in sorted(ok_items, key=lambda x: x.price or 0):
            rc   = _row_class(p, best, worst)
            note = _note(p, best, worst)
            rows_html += f"""
              <tr class="{rc}">
                <td>{p.site}</td>
                <td><a href="{p.url}" target="_blank" rel="noopener">{p.name[:60]}</a></td>
                <td>{p.seller or "—"}</td>
                <td class="text-end fw-bold">{fmt_price(p.price)}</td>
                <td class="text-end">{fmt_price(p.price_pgr)}/g</td>
                <td>{note}</td>
              </tr>"""

        # OOS and error items are intentionally not shown in HTML —
        # only in-stock products with confirmed prices are displayed.

        if best:
            savings = ""
            if worst and best.price and worst.price and best.price != worst.price:
                diff = worst.price - best.price
                pct  = diff / worst.price * 100
                savings = (f'<div class="alert alert-success py-1 mt-2 mb-0 small">'
                           f'💰 En ucuz: <strong>{best.site}</strong> — '
                           f'{fmt_price(best.price)} ({fmt_price(best.price_pgr)}/g) &nbsp;|&nbsp; '
                           f'En pahalıya göre <strong>{fmt_price(diff)} ({pct:.1f}%)</strong> tasarruf</div>')
            best_deals_rows += f"""
              <tr>
                <td><strong>{weight}</strong></td>
                <td>{best.site}</td>
                <td>{best.seller or "—"}</td>
                <td class="text-end fw-bold text-success">{fmt_price(best.price)}</td>
                <td class="text-end">{fmt_price(best.price_pgr)}/g</td>
                <td><a href="{best.url}" target="_blank" rel="noopener" class="btn btn-sm btn-outline-primary">🔗 Görüntüle</a></td>
              </tr>"""
        else:
            savings = ""

        weight_sections += f"""
        <div class="card mb-4 shadow-sm">
          <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
            <span>⚖️ <strong>{weight}</strong> &nbsp;·&nbsp; {grams}g · 22 Ayar · 916‰</span>
            {"<span class='badge bg-success'>✓ " + str(len(ok_items)) + " ürün</span>" if ok_items else "<span class='badge bg-danger'>Ürün bulunamadı</span>"}
          </div>
          <div class="card-body p-0">
            <table class="table table-hover mb-0">
              <thead class="table-light">
                <tr>
                  <th>Site</th><th>Ürün</th><th>Satıcı</th>
                  <th class="text-end">Fiyat (TRY)</th>
                  <th class="text-end">Gram Fiyatı</th>
                  <th>Not</th>
                </tr>
              </thead>
              <tbody>{rows_html}</tbody>
            </table>
          </div>
          {f'<div class="card-footer bg-white">{savings}</div>' if savings else ""}
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>22 Ayar Altın Bilezik Fiyat Karşılaştırma</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {{ background: #f8f9fa; }}
    .hero {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
             color: white; padding: 2.5rem 0 2rem; }}
    .hero h1 {{ font-size: 1.8rem; font-weight: 700; }}
    .updated-badge {{ font-size: .85rem; opacity: .8; }}
    .table td, .table th {{ vertical-align: middle; }}
    .table-success td {{ color: #0a3622 !important; }}
    a {{ text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .footer {{ font-size: .8rem; color: #6c757d; padding: 1.5rem 0; text-align: center; }}
  </style>
</head>
<body>

<div class="hero">
  <div class="container">
    <h1>💛 22 Ayar Altın Bilezik Fiyat Karşılaştırma</h1>
    <p class="updated-badge mb-1">
      🕐 Son güncelleme: <strong>{ts}</strong> {gold_info}
    </p>
    <p class="updated-badge mb-0 opacity-75">
      Hepsiburada · Amazon TR · N11 · Idefix &nbsp;|&nbsp;
      Sadece stokta olan ürünler gösterilmektedir
    </p>
  </div>
</div>

<div class="container mt-4">

  <!-- Best Deals Summary -->
  <div class="card mb-4 border-warning shadow">
    <div class="card-header bg-warning text-dark fw-bold">✅ En İyi Fırsatlar Özeti</div>
    <div class="card-body p-0">
      <table class="table table-hover mb-0">
        <thead class="table-light">
          <tr>
            <th>Ağırlık</th><th>Site</th><th>Satıcı</th>
            <th class="text-end">En Düşük Fiyat</th>
            <th class="text-end">Gram Fiyatı</th>
            <th>Link</th>
          </tr>
        </thead>
        <tbody>{best_deals_rows}</tbody>
      </table>
    </div>
  </div>

  <!-- Per-weight sections -->
  {weight_sections}

</div>

<div class="footer">
  <div class="container">
    Veriler otomatik olarak her gün güncellenir. Fiyatlar anlık değişkenlik gösterebilir.
    Satın alma kararı vermeden önce ilgili siteden teyit ediniz.
  </div>
</div>

</body>
</html>"""


def save_html(products: List[Product], path: str,
              live_gold_price: Optional[float] = None) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    html = generate_html(products, live_gold_price)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    log.info(f"  💾 HTML saved → {path}")


# ══════════════════════════════════════════════════════════════════════════════
#  STARTUP CHECKS & ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def preflight() -> bool:
    ok = True
    if not PW_OK:
        print(f"{C_RED}[ERROR] Playwright not installed.{C_RESET}")
        print("  Fix: pip3 install playwright && python3 -m playwright install chromium")
        ok = False
    if not TABULATE_OK:
        print(f"{C_YELLOW}[WARN]  tabulate not installed — plain-text tables will be used.{C_RESET}")
    if not COLOR_OK:
        print("[WARN]  colorama not installed — output will be monochrome.")
    if sum(len(v) for v in PRODUCT_URLS.values()) == 0:
        print(f"{C_YELLOW}[WARN]  No product URLs configured.{C_RESET}")
    return ok


async def _main(args: argparse.Namespace) -> None:
    global MIN_PRICE_PER_GRAM_TRY, MAX_PRICE_PER_GRAM_TRY

    total = sum(len(v) for v in PRODUCT_URLS.values())
    print()
    print("╔" + "═" * 62 + "╗")
    print("║   22 Ayar Gold Bracelet — Price Comparison Scraper PRO    ║")
    print("╠" + "═" * 62 + "╣")
    print(f"║  Engine  : Playwright (headless Chromium)                 ║")
    print(f"║  URLs    : {total:<52}║")
    print(f"║  Delay   : {MIN_DELAY_SEC:.1f}–{MAX_DELAY_SEC:.1f}s (randomised)                       ║")
    print(f"║  UA Pool : {len(USER_AGENTS)} user-agents                                ║")
    print("╚" + "═" * 62 + "╝")
    print()

    if not preflight():
        sys.exit(1)

    # ── Fetch live gold price and set dynamic sanity threshold ────────────────
    print("  🔍 Fetching live 22-ayar gold price …")
    live_22k = fetch_live_gold_price_try()
    if live_22k:
        MIN_PRICE_PER_GRAM_TRY = round(live_22k * SANITY_RATIO, 2)
        MAX_PRICE_PER_GRAM_TRY = round(live_22k * MAX_SANITY_RATIO, 2)
        print(f"  ✓  Live 22k price  : {fmt_price(live_22k)}/g")
        print(f"  ✓  Min valid price : {fmt_price(MIN_PRICE_PER_GRAM_TRY)}/g "
              f"({SANITY_RATIO*100:.0f}% of market — products below this are skipped)")
        print(f"  ✓  Max valid price : {fmt_price(MAX_PRICE_PER_GRAM_TRY)}/g "
              f"({MAX_SANITY_RATIO*100:.0f}% of market — absurd prices above this are skipped)")
    else:
        print(f"  ⚠  Could not fetch live price — using fallback "
              f"min={fmt_price(MIN_PRICE_PER_GRAM_TRY)}/g  max={fmt_price(MAX_PRICE_PER_GRAM_TRY)}/g")
    print()

    products = await scrape_all(PRODUCT_URLS)
    if not products:
        print("No results to display.")
        return

    compare(products)

    if args.html:
        save_html(products, args.html_output, live_gold_price=live_22k)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="22 Ayar Altın Bilezik Fiyat Karşılaştırma Scraper",
    )
    parser.add_argument(
        "--html", action="store_true",
        help="HTML çıktısı da oluştur (GitHub Pages için)",
    )
    parser.add_argument(
        "--html-output", default="docs/index.html", metavar="PATH",
        help="HTML dosyasının kaydedileceği yol (varsayılan: docs/index.html)",
    )
    parser.add_argument(
        "--no-terminal", action="store_true",
        help="Terminal çıktısını gizle (yalnızca HTML modu)",
    )
    args = parser.parse_args()
    asyncio.run(_main(args))


if __name__ == "__main__":
    main()
