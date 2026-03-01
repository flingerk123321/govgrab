"""GovGrab — Utility functions and configuration."""
from __future__ import annotations

import json
import logging
import os
import re
import glob as glob_module
from datetime import datetime

logger = logging.getLogger("govgrab")


def get_secret(key, default=""):
    """Get a secret from os.environ or st.secrets (Streamlit Cloud)."""
    val = os.environ.get(key, "")
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(key, default)
    except Exception:
        return default

# ── Config ──
APP_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED_SEARCHES_FILE = os.path.join(APP_DIR, "saved_searches.json")
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")
BLOG_DIR = os.path.join(APP_DIR, "blog")
CACHE_DIR = os.path.join(APP_DIR, ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

PLATFORM_FEES = {
    "GSA Auctions": {"buyer_premium": 0.0, "note": "No buyer's premium"},
    "GovDeals": {"buyer_premium": 0.125, "note": "12.5% buyer's premium (typical)"},
    "PublicSurplus": {"buyer_premium": 0.0, "note": "No buyer's premium (varies by seller)"},
    "Municibid": {"buyer_premium": 0.09, "note": "9% buyer's fee"},
}

CATEGORIES = [
    "All Categories", "Vehicles", "Heavy Equipment", "Electronics & IT",
    "Office Furniture", "Tools & Industrial", "Medical Equipment",
    "Real Estate & Land", "Agricultural", "Other",
]

US_STATES = [
    "All States", "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI",
    "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND",
    "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA",
    "WA", "WV", "WI", "WY", "DC",
]

CATEGORY_KEYWORDS = {
    "Vehicles": ["car", "truck", "van", "suv", "sedan", "vehicle", "bus", "ambulance",
                  "ford", "chevy", "chevrolet", "dodge", "toyota", "honda", "gmc",
                  "pickup", "cruiser", "police", "motorcycle", "trailer", "boat", "vessel"],
    "Heavy Equipment": ["excavator", "loader", "backhoe", "bulldozer", "crane", "forklift",
                         "tractor", "mower", "generator", "compressor", "pump", "caterpillar",
                         "cat ", "john deere", "bobcat", "kubota", "case ", "komatsu"],
    "Electronics & IT": ["computer", "laptop", "monitor", "printer", "server", "ipad",
                          "macbook", "dell", "hp ", "lenovo", "cisco", "router", "switch",
                          "projector", "camera", "phone", "iphone", "radio", "electronics"],
    "Office Furniture": ["desk", "chair", "table", "cabinet", "filing", "cubicle",
                          "bookcase", "shelf", "furniture", "office"],
    "Tools & Industrial": ["tool", "drill", "saw", "welder", "compressor", "wrench",
                            "equipment", "industrial", "shop", "hand tools", "power tools"],
    "Medical Equipment": ["medical", "dental", "hospital", "surgical", "x-ray",
                           "wheelchair", "stretcher", "defibrillator", "lab "],
    "Real Estate & Land": ["acre", "land", "property", "building", "parcel", "lot ",
                            "real estate", "house", "structure"],
    "Agricultural": ["farm", "agricultural", "irrigation", "hay", "livestock",
                      "tractor", "harvester", "grain", "seed"],
}


def sanitize_keyword(text: str) -> str:
    """Strip HTML/script tags and dangerous characters from user input."""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[<>"\';]', '', text)
    return text.strip()


def detect_category(title):
    t = title.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in t:
                return cat
    return "Other"


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE) as f:
            s = json.load(f)
    else:
        s = {"gsa_api_key": "", "zip_code": "", "radius_miles": 100}
    env_key = get_secret("GSA_API_KEY", "")
    if env_key:
        s["gsa_api_key"] = env_key
    return s


def save_settings(s):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(s, f, indent=2)


def load_saved_searches():
    if os.path.exists(SAVED_SEARCHES_FILE):
        with open(SAVED_SEARCHES_FILE) as f:
            return json.load(f)
    return []


def save_saved_searches(searches):
    with open(SAVED_SEARCHES_FILE, "w") as f:
        json.dump(searches, f, indent=2)


def parse_price(text):
    if not text:
        return None
    m = re.search(r'\$?([\d,]+\.?\d*)', str(text).replace(",", ""))
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return None
    return None


def parse_date(text):
    if not text:
        return None
    text = text.strip()
    for fmt in ["%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %I:%M %p",
                "%m/%d/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"]:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def compute_true_cost(price, platform):
    if price is None:
        return None
    fee = PLATFORM_FEES.get(platform, {}).get("buyer_premium", 0)
    return round(price * (1 + fee), 2)


# ── Blog helpers ──
BLOG_BANNERS = {
    "how-to-buy-government-surplus-vehicles": {"emoji": "\U0001F699", "grad": "linear-gradient(135deg, #0EA5E9, #3B82F6)"},
    "police-auction-cars": {"emoji": "\U0001F6A8", "grad": "linear-gradient(135deg, #EC4899, #F43F5E)"},
    "heavy-equipment-government-auctions": {"emoji": "\U0001F3D7\uFE0F", "grad": "linear-gradient(135deg, #F59E0B, #F97316)"},
    "government-surplus-laptops-electronics": {"emoji": "\U0001F4BB", "grad": "linear-gradient(135deg, #A855F7, #7C3AED)"},
    "gsa-auctions-guide": {"emoji": "\U0001F3DB\uFE0F", "grad": "linear-gradient(135deg, #10B981, #059669)"},
    "govdeals-vs-publicsurplus": {"emoji": "\u2696\uFE0F", "grad": "linear-gradient(135deg, #0EA5E9, #A855F7)"},
    "flipping-government-auction-items": {"emoji": "\U0001F4B0", "grad": "linear-gradient(135deg, #22C55E, #84CC16)"},
    "best-government-auction-sites-2026": {"emoji": "\U0001F3C6", "grad": "linear-gradient(135deg, #F59E0B, #EAB308)"},
    "government-auction-pickup-guide": {"emoji": "\U0001F69A", "grad": "linear-gradient(135deg, #6366F1, #3B82F6)"},
    "state-surplus-auctions": {"emoji": "\U0001F5FA\uFE0F", "grad": "linear-gradient(135deg, #14B8A6, #0EA5E9)"},
    "5-tips-government-auctions": {"emoji": "\U0001F4A1", "grad": "linear-gradient(135deg, #F97316, #F59E0B)"},
    "understanding-buyers-premiums": {"emoji": "\U0001F4CA", "grad": "linear-gradient(135deg, #EC4899, #A855F7)"},
    "what-is-govgrab": {"emoji": "\U0001F50D", "grad": "linear-gradient(135deg, #0EA5E9, #22D3EE)"},
}
BLOG_DEFAULT_BANNER = {"emoji": "\U0001F4D6", "grad": "linear-gradient(135deg, #64748B, #475569)"}


def get_blog_banner_html(slug, height="140px"):
    b = BLOG_BANNERS.get(slug, BLOG_DEFAULT_BANNER)
    return (
        f'<div class="blog-banner" style="background:{b["grad"]};height:{height};">'
        f'<span>{b["emoji"]}</span></div>'
    )


def load_blog_posts():
    posts = []
    if not os.path.isdir(BLOG_DIR):
        return posts
    for fpath in sorted(glob_module.glob(os.path.join(BLOG_DIR, "*.md")), reverse=True):
        with open(fpath) as f:
            content = f.read()
        meta = {}
        body = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        meta[key.strip()] = val.strip()
                body = parts[2].strip()
        slug = os.path.splitext(os.path.basename(fpath))[0]
        posts.append({"slug": slug, "meta": meta, "body": body, "path": fpath})
    posts.sort(key=lambda p: p["meta"].get("date", ""), reverse=True)
    return posts
