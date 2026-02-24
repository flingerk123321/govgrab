#!/usr/bin/env python3
"""GovGrab — Government Surplus Auction Aggregator
Aggregates listings from GSA Auctions, GovDeals, PublicSurplus, and Municibid.
"""
from __future__ import annotations

import streamlit as st
import requests
import json
import os
import re
import time
import math
import subprocess
import glob as glob_module
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlencode


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
            return json.load(f)
    return {"gsa_api_key": "", "zip_code": "", "radius_miles": 100}


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


# ── Navigation helper ──
def navigate_to(page_name, **kwargs):
    """Navigate to a page and pass params via session state."""
    st.session_state["_nav_page"] = page_name
    for k, v in kwargs.items():
        st.session_state[k] = v


# ══════════════════════════════════════════════════════
# Blog helpers
# ══════════════════════════════════════════════════════
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


# ══════════════════════════════════════════════════════
# Scrapers
# ══════════════════════════════════════════════════════
def _curl_get(url):
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "-A", UA, "--max-time", "15", url],
            capture_output=True, text=True, timeout=20,
        )
        if result.returncode == 0 and len(result.stdout) > 100:
            return result.stdout
    except Exception:
        pass
    return None


@st.cache_data(ttl=900)
def fetch_gsa_listings(api_key):
    if not api_key:
        return []
    try:
        url = f"https://api.gsa.gov/assets/gsaauctions/v2/auctions?api_key={api_key}&format=JSON"
        resp = requests.get(url, timeout=30, allow_redirects=True)
        if resp.status_code in (429, 403):
            return []
        if resp.status_code != 200:
            return []
        data = resp.json()
        listings = []
        items = data if isinstance(data, list) else data.get("results", data.get("auctions", []))
        if isinstance(data, dict) and not items:
            items = [data]
        for item in items:
            end_date = parse_date(item.get("aucEndDt", ""))
            high_bid = item.get("highBidAmount")
            price = float(high_bid) if high_bid and high_bid != 0 else None
            title = item.get("itemName", "Unknown")
            desc_html = item.get("lotInfo", "")
            desc_soup = BeautifulSoup(desc_html, "html.parser")
            desc_text = desc_soup.get_text(separator=" ", strip=True)[:500]
            listings.append({
                "id": f"gsa-{item.get('saleNo', '')}-{item.get('lotNo', '')}",
                "platform": "GSA Auctions", "title": title, "description": desc_text,
                "current_bid": price, "num_bids": item.get("biddersCount") or 0,
                "end_date": end_date.isoformat() if end_date else None, "end_date_dt": end_date,
                "city": item.get("propertyCity", "").strip(), "state": item.get("propertyState", "").strip(),
                "zip_code": item.get("propertyZip", "").replace("null", "").strip(),
                "seller": item.get("agencyName", ""), "url": item.get("itemDescURL", ""),
                "image_url": item.get("imageURL", ""), "category": detect_category(title),
                "buyer_premium": 0.0,
            })
        return listings
    except Exception:
        return []


@st.cache_data(ttl=600)
def fetch_publicsurplus_listings(keyword="", state="", max_pages=3):
    listings = []
    for page_num in range(max_pages):
        start = page_num * 25 + 1
        params = {"posting": "y", "keyword": keyword,
                  "state": state if state != "All States" else "",
                  "sortField": "enddate", "sortDir": "ASC",
                  "start": str(start), "num": "25"}
        url = f"https://www.publicsurplus.com/sms/browse/search?{urlencode(params)}"
        html = _curl_get(url)
        if not html:
            break
        soup = BeautifulSoup(html, "html.parser")
        items = soup.find_all("div", class_="auction-item")
        if not items:
            break
        for item in items:
            try:
                title_link = None
                for a in item.find_all("a", href=lambda h: h and "auction/view" in str(h)):
                    t = a.get_text(strip=True)
                    if t and len(t) > 3:
                        title_link = a
                        break
                if not title_link:
                    continue
                raw_title = title_link.get_text(strip=True)
                href = title_link.get("href", "")
                auc_id = ""
                m = re.search(r'auc=(\d+)', href)
                if m:
                    auc_id = m.group(1)
                title = re.sub(r'^#\d+\s*-\s*', '', raw_title).strip()
                full_url = f"https://www.publicsurplus.com{href}" if href.startswith("/") else href
                img = item.find("img")
                img_url = img.get("src", "") if img else ""
                # Use large image instead of tiny thumbnail
                img_url = img_url.replace("/thumb-b/", "/thumb-l/")
                full_text = item.get_text()
                price = None
                price_match = re.search(r'Price:\s*\$?([\d,]+\.?\d*)', full_text)
                if price_match:
                    price = parse_price(price_match.group(1))
                time_match = re.search(r'Time Left:\s*(.+?)(?:\n|$)', full_text)
                time_left = time_match.group(1).strip() if time_match else ""
                item_state = ""
                state_el = item.find("span", class_="auction-item-state")
                if state_el:
                    item_state = state_el.get_text(strip=True)
                listings.append({
                    "id": f"ps-{auc_id}", "platform": "PublicSurplus",
                    "title": title or raw_title, "description": "",
                    "current_bid": price, "num_bids": None,
                    "end_date": None, "end_date_dt": None, "time_left": time_left,
                    "city": "", "state": item_state, "zip_code": "", "seller": "",
                    "url": full_url, "image_url": img_url,
                    "category": detect_category(title or raw_title), "buyer_premium": 0.0,
                })
            except Exception:
                continue
        if len(items) < 25:
            break
        time.sleep(0.5)
    return listings


@st.cache_data(ttl=600)
def fetch_municibid_listings(keyword="", state="", max_pages=3):
    listings = []
    base_url = "https://municibid.com"
    for page_num in range(1, max_pages + 1):
        if keyword:
            url = f"{base_url}/Search?query={quote_plus(keyword)}&page={page_num}"
        else:
            url = f"{base_url}/Browse?page={page_num}"
        html = _curl_get(url)
        if not html:
            break
        soup = BeautifulSoup(html, "html.parser")
        items = soup.find_all("div", class_="browse-item")
        if not items:
            break
        for item in items:
            try:
                listing_id = item.get("data-listingid", "")
                title = ""
                href = ""
                for a in item.find_all("a", href=lambda h: h and "/Listing/Details/" in str(h)):
                    t = a.get_text(strip=True)
                    if t and len(t) > 2:
                        title = t
                        href = a["href"]
                        break
                    elif not href and a.get("href"):
                        href = a["href"]
                img = item.find("img")
                img_url = img.get("src", "") if img else ""
                # Use full-size image instead of thumbnail crop
                img_url = img_url.replace("_thumbcrop.jpg", "_fullsize.jpg")
                if not title and img and img.get("alt"):
                    title = img["alt"].strip()
                if not title and href:
                    slug = href.rstrip("/").split("/")[-1].replace("-", " ")
                    if slug and len(slug) > 2:
                        title = slug
                if not title:
                    continue
                full_url = f"{base_url}{href}" if href.startswith("/") else href
                bid_span = item.find("span", class_=lambda c: c and "awe-rt-CurrentPrice" in str(c))
                current_bid = parse_price(bid_span.get_text()) if bid_span else None
                bids_span = item.find("span", class_=lambda c: c and "awe-rt-AcceptedListingActionCount" in str(c))
                num_bids = None
                if bids_span:
                    try:
                        num_bids = int(bids_span.get_text(strip=True))
                    except ValueError:
                        pass
                city, item_state = "", ""
                for s in item.find_all("span"):
                    t = s.get_text(strip=True)
                    if "," in t and len(t) < 50 and not t.startswith("$"):
                        parts = t.split(",")
                        if len(parts) == 2:
                            city = parts[0].strip()
                            item_state = parts[1].strip()
                            break
                if state and state != "All States" and item_state and item_state != state:
                    continue
                end_date_dt = None
                full_text = item.get_text()
                end_match = re.search(r'Ended?:\s*([\d/]+ [\d:]+\s*[APM]*)', full_text)
                if end_match:
                    end_date_dt = parse_date(end_match.group(1).strip())
                seller = ""
                pipe_parts = full_text.split("|")
                if len(pipe_parts) >= 2:
                    seller = pipe_parts[1].strip().split("\n")[0].strip()
                listings.append({
                    "id": f"muni-{listing_id}", "platform": "Municibid",
                    "title": title, "description": "",
                    "current_bid": current_bid, "num_bids": num_bids,
                    "end_date": end_date_dt.isoformat() if end_date_dt else None,
                    "end_date_dt": end_date_dt, "time_left": "",
                    "city": city, "state": item_state, "zip_code": "", "seller": seller,
                    "url": full_url, "image_url": img_url,
                    "category": detect_category(title), "buyer_premium": 0.09,
                })
            except Exception:
                continue
        if len(items) < 20:
            break
        time.sleep(0.5)
    return listings


GOVDEALS_API_URL = "https://maestro.lqdt1.com/search/list"
GOVDEALS_API_KEY = "REDACTED_GOVDEALS_KEY"
GOVDEALS_IMG_BASE = "https://webassets.lqdt1.com/assets/photos/"


@st.cache_data(ttl=600)
def fetch_govdeals_listings(keyword="", state="", max_pages=3):
    """Fetch GovDeals listings via their public frontend API."""
    listings = []
    rows_per_page = 25
    for page_num in range(1, max_pages + 1):
        try:
            import uuid
            body = {
                "businessId": "GD",
                "searchText": keyword or "*",
                "page": page_num,
                "displayRows": rows_per_page,
                "sessionId": str(uuid.uuid4()),
                "facetLimit": 10,
                "facetsShortened": False,
                "isVehicleSearch": False,
                "isSimpleTimeSearch": False,
                "isQAL": False,
                "categoryIds": "",
                "locationId": "",
                "model": "",
                "makebrand": "",
                "eventId": "",
                "auctionTypeId": "",
                "sortField": "default",
                "sortOrder": "asc",
                "requestType": "",
                "responseStyle": "",
                "facets": "",
                "facetsFilter": "",
                "timeType": "",
                "sellerTypeId": "",
                "accountIds": "",
                "zipcode": "",
                "proximityWithinDistance": 0,
                "simpleTimeSearchType": "",
                "simpleTimeWithIn": 0,
                "rangeTimeSearchType": "",
                "toDate": "",
                "fromDate": "",
                "timeUnitValue": 0,
                "modelYear": "",
            }
            resp = requests.post(
                GOVDEALS_API_URL,
                headers={
                    "x-api-key": GOVDEALS_API_KEY,
                    "x-user-id": "1",
                    "x-api-correlation-id": str(uuid.uuid4()),
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Origin": "https://www.govdeals.com",
                    "Referer": "https://www.govdeals.com/",
                    "User-Agent": UA,
                },
                json=body,
                timeout=15,
            )
            if resp.status_code != 200:
                break
            data = resp.json()
            items = data.get("assetSearchResults", [])
            if not items:
                break
            for item in items:
                if item.get("businessId") != "GD":
                    continue
                item_state = (item.get("locationState") or "").strip()
                if state and state != "All States" and item_state and item_state != state:
                    continue
                title = item.get("assetShortDescription", "Unknown")
                account_id = item.get("accountId", "")
                asset_id = item.get("assetId", "")
                detail_url = f"https://www.govdeals.com/asset/{asset_id}/{account_id}"
                photo = item.get("photo", "")
                img_url = f"{GOVDEALS_IMG_BASE}{account_id}/{photo}&w=400" if photo else ""
                end_str = item.get("assetAuctionEndDate", "")
                end_date_dt = None
                if end_str:
                    try:
                        end_date_dt = datetime.fromisoformat(end_str)
                    except (ValueError, TypeError):
                        end_date_dt = parse_date(end_str)
                time_remaining = item.get("timeRemaining", "")
                listings.append({
                    "id": f"gd-{account_id}-{asset_id}",
                    "platform": "GovDeals",
                    "title": title,
                    "description": "",
                    "current_bid": item.get("currentBid"),
                    "num_bids": item.get("bidCount"),
                    "end_date": end_date_dt.isoformat() if end_date_dt else None,
                    "end_date_dt": end_date_dt,
                    "time_left": time_remaining,
                    "city": (item.get("locationCity") or "").strip(),
                    "state": item_state,
                    "zip_code": (item.get("locationZip") or "").strip(),
                    "seller": (item.get("companyName") or "").strip(),
                    "url": detail_url,
                    "image_url": img_url,
                    "category": detect_category(title),
                    "buyer_premium": 0.125,
                })
            if len(items) < rows_per_page:
                break
        except Exception as e:
            import traceback
            print(f"GovDeals scraper error: {e}")
            traceback.print_exc()
            break
        time.sleep(0.5)
    return listings


def fetch_all_listings(keyword, state, platforms, gsa_api_key):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    all_listings = []
    futures = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        if "GSA Auctions" in platforms and gsa_api_key:
            futures[pool.submit(fetch_gsa_listings, gsa_api_key)] = "GSA Auctions"
        if "GovDeals" in platforms:
            futures[pool.submit(fetch_govdeals_listings, keyword, state)] = "GovDeals"
        if "PublicSurplus" in platforms:
            futures[pool.submit(fetch_publicsurplus_listings, keyword, state)] = "PublicSurplus"
        if "Municibid" in platforms:
            futures[pool.submit(fetch_municibid_listings, keyword, state)] = "Municibid"
        for future in as_completed(futures):
            name = futures[future]
            try:
                results = future.result(timeout=30)
                if name == "GSA Auctions":
                    if keyword:
                        kw = keyword.lower()
                        results = [l for l in results if kw in l["title"].lower() or kw in l.get("description", "").lower()]
                    if state and state != "All States":
                        results = [l for l in results if l["state"] == state]
                all_listings.extend(results)
            except Exception:
                pass
    return all_listings


# ══════════════════════════════════════════════════════
# Rendering helpers
# ══════════════════════════════════════════════════════
def render_listing_card(listing, show_true_cost=True):
    """Render a single listing as an eBay-style card with large image."""
    badge_colors = {"GSA Auctions": "#3B82F6", "GovDeals": "#10B981", "PublicSurplus": "#A855F7", "Municibid": "#F97316"}
    badge_color = badge_colors.get(listing["platform"], "#64748b")

    img_src = listing.get("image_url", "")
    if img_src:
        img_html = (
            f'<img src="{img_src}" alt="" '
            'style="width:100%;height:100%;object-fit:cover;" '
            'onerror="this.style.display=&quot;none&quot;;this.nextElementSibling.style.display=&quot;flex&quot;">'
            '<div style="display:none;align-items:center;justify-content:center;'
            'width:100%;height:100%;color:#475569;font-size:40px;background:#111118;">&#128247;</div>'
        )
    else:
        img_html = ('<div style="display:flex;align-items:center;justify-content:center;'
                     'height:100%;color:#475569;font-size:40px;background:#111118;">&#128247;</div>')

    price_html = ""
    if listing["current_bid"] is not None:
        price_html = f'<div class="card-price">${listing["current_bid"]:,.2f}</div>'
        if show_true_cost and listing.get("buyer_premium", 0) > 0:
            tc = compute_true_cost(listing["current_bid"], listing["platform"])
            price_html += f'<div class="card-true-cost">+{listing["buyer_premium"]*100:.0f}% fee = ${tc:,.2f}</div>'
    else:
        price_html = '<div class="card-price" style="color:#94a3b8;font-size:14px;">No bids yet</div>'

    loc_parts = []
    if listing.get("city"):
        loc_parts.append(listing["city"])
    if listing.get("state"):
        loc_parts.append(listing["state"])
    location = ", ".join(loc_parts)

    time_html = ""
    if listing.get("time_left"):
        tl = listing["time_left"]
        is_urgent = "min" in tl.lower() or "hour" in tl.lower()
        cls = "card-time-urgent" if is_urgent else "card-time"
        time_html = f'<div class="{cls}">{tl}</div>'
    elif listing.get("end_date_dt"):
        dt = listing["end_date_dt"]
        now = datetime.now()
        if dt > now:
            delta = dt - now
            if delta.days == 0:
                h = delta.seconds // 3600
                m = (delta.seconds % 3600) // 60
                time_html = f'<div class="card-time-urgent">{h}h {m}m left</div>'
            elif delta.days <= 2:
                time_html = f'<div class="card-time-urgent">{delta.days}d {delta.seconds // 3600}h left</div>'
            else:
                time_html = f'<div class="card-time">Ends {dt.strftime("%b %d")}</div>'

    bids_html = ""
    if listing.get("num_bids") is not None and listing["num_bids"] > 0:
        bids_html = f'<span class="card-bids">{listing["num_bids"]} bid{"s" if listing["num_bids"] != 1 else ""}</span>'

    time_overlay = f'<div class="card-time-overlay">{time_html}</div>' if time_html else ''

    # No leading whitespace — Markdown interprets 4 spaces as a code block
    return (
        f'<a href="{listing["url"]}" target="_blank" class="card-link">'
        f'<div class="listing-card">'
        f'<div class="card-img-wrap">'
        f'{img_html}'
        f'<div class="card-badge" style="background:{badge_color};box-shadow:0 0 8px {badge_color}80;">{listing["platform"]}</div>'
        f'{time_overlay}'
        f'</div>'
        f'<div class="card-body">'
        f'<div class="card-title">{listing["title"]}</div>'
        f'<div class="card-location">{location}</div>'
        f'<div class="card-price-row">{price_html}{bids_html}</div>'
        f'</div>'
        f'</div>'
        f'</a>'
    )


def render_listing_grid(listings, cols=3, show_true_cost=True):
    """Render a grid of listing cards."""
    if not listings:
        return
    html_cards = [render_listing_card(l, show_true_cost) for l in listings]
    grid_html = f'<div class="listing-grid listing-grid-{cols}">{"".join(html_cards)}</div>'
    st.markdown(grid_html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# STREAMLIT APP
# ══════════════════════════════════════════════════════
st.set_page_config(page_title="GovGrab", page_icon="https://em-content.zobj.net/source/twitter/376/classical-building_1f3db-fe0f.png", layout="wide", initial_sidebar_state="expanded")

# ── Handle navigation from session state ──
PAGES = ["Home", "Search", "Ending Soon", "Saved Searches", "Blog", "Settings"]
if "_nav_page" in st.session_state:
    nav_target = st.session_state.pop("_nav_page")
    if nav_target in PAGES:
        st.session_state["_page_radio"] = nav_target

# ── Global CSS ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
div[data-testid="stToolbar"] {display: none;}
.stDeployButton {display: none;}

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* ── Dark theme globals ── */
.stApp, [data-testid="stAppViewContainer"], .main, .block-container {
    background-color: #111118 !important;
    color: #CBD5E1 !important;
}
.block-container { padding-top: 1rem; max-width: 1280px; }

/* Override Streamlit widget styles for dark theme */
input, textarea,
[data-baseweb="select"], [data-baseweb="input"],
[data-baseweb="base-input"], [data-baseweb="input-container"],
.stTextInput > div > div, .stNumberInput > div > div,
.stSelectbox > div > div, .stMultiSelect > div > div,
.stTextArea > div > div {
    background-color: #232334 !important;
    color: #F8FAFC !important;
    border-color: #3D4560 !important;
}
input::placeholder, textarea::placeholder { color: #8891A5 !important; opacity: 1 !important; }
/* Selectbox placeholder text */
[data-baseweb="select"] span, [data-baseweb="select"] div[aria-selected] { color: #F8FAFC !important; }
input:focus, textarea:focus {
    border-color: #0EA5E9 !important;
    box-shadow: 0 0 0 1px #0EA5E9 !important;
    background-color: #2A2A3D !important;
}
[data-baseweb="select"] > div,
[data-baseweb="select"] > div > div { background-color: #232334 !important; }
[data-baseweb="popover"], [data-baseweb="popover"] > div { background-color: #232334 !important; border: 1px solid #3D4560 !important; }
[data-baseweb="menu"], [role="listbox"] { background-color: #232334 !important; }
[data-baseweb="menu"] li, [role="option"] { color: #E2E8F0 !important; }
[data-baseweb="menu"] li:hover, [role="option"]:hover,
[data-baseweb="menu"] li[aria-selected="true"], [role="option"][aria-selected="true"] { background-color: #2A2A3D !important; }
/* Number input steppers */
.stNumberInput button { background-color: #232334 !important; color: #CBD5E1 !important; border-color: #3D4560 !important; }
.stNumberInput button:hover { background-color: #2A2A3D !important; color: #F8FAFC !important; }
/* Make sure nested inputs are transparent on their bg */
[data-baseweb="input"] input, [data-baseweb="base-input"] input { background-color: transparent !important; }
label, .stTextInput label, .stSelectbox label, .stNumberInput label { color: #E2E8F0 !important; }
.stMarkdown, .stMarkdown p { color: #E2E8F0 !important; }
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 { color: #F8FAFC !important; }
.stMarkdown a { color: #0EA5E9 !important; }
.stMarkdown strong { color: #F8FAFC !important; }
.stCaption, [data-testid="stCaptionContainer"] { color: #94A3B8 !important; }
hr { border-color: #2D3748 !important; }

/* Streamlit buttons */
.stButton > button {
    background: linear-gradient(135deg, #0EA5E9, #0284C7) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    box-shadow: 0 0 20px rgba(14, 165, 233, 0.4) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    background: #1A1A24 !important;
    border: 1px solid #2D3748 !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #0EA5E9 !important;
    box-shadow: 0 0 12px rgba(14, 165, 233, 0.2) !important;
}

/* Checkbox & slider */
.stCheckbox label span { color: #E2E8F0 !important; }
.stCheckbox [data-testid="stCheckbox"] { color: #E2E8F0 !important; }
[data-testid="stSlider"] { color: #E2E8F0 !important; }
[data-testid="stSlider"] [data-testid="stTickBarMin"],
[data-testid="stSlider"] [data-testid="stTickBarMax"] { color: #94A3B8 !important; }

/* Spinner */
.stSpinner > div { color: #0EA5E9 !important; }

/* Info / Warning / Success boxes */
[data-testid="stAlert"] { background-color: #1A1A24 !important; border-color: #2D3748 !important; color: #CBD5E1 !important; }

/* Dark scrollbar */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #111118; }
::-webkit-scrollbar-thumb { background: #1E293B; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #334155; }

/* ── Animations ── */
@keyframes gradientShift {
    0% { transform: translate(-50%, -50%) rotate(0deg); }
    50% { transform: translate(-50%, -50%) rotate(180deg); }
    100% { transform: translate(-50%, -50%) rotate(360deg); }
}
@keyframes pulseUrgent {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

/* ── Compact Hero ── */
.hero-compact {
    background: linear-gradient(135deg, #111118 0%, #1A1A24 100%);
    border-radius: 14px;
    padding: 32px 36px 28px 36px;
    margin-bottom: 16px;
    position: relative;
    overflow: hidden;
    border: 1px solid #2D3748;
}
.hero-compact::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, #0EA5E9, #A855F7, transparent);
}
.hero-compact::after {
    content: '';
    position: absolute;
    top: -50%; left: -50%; width: 200%; height: 200%;
    background: radial-gradient(circle at 30% 50%, rgba(14,165,233,0.06) 0%, transparent 50%),
                radial-gradient(circle at 70% 80%, rgba(168,85,247,0.04) 0%, transparent 50%);
    pointer-events: none;
}
.hero-text { position: relative; z-index: 1; }
.hero-compact h1 { color: #F8FAFC; font-size: 32px; font-weight: 900; margin-bottom: 6px; letter-spacing: -0.5px; }
.hero-compact p { color: #94A3B8; font-size: 15px; margin: 0; line-height: 1.5; }
.hero-compact .hl {
    background: linear-gradient(135deg, #0EA5E9, #22D3EE);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero-stats {
    display: flex; gap: 24px; margin-top: 16px;
    position: relative; z-index: 1;
}
.hero-stat {
    font-size: 13px; color: #94A3B8;
}
.hero-stat strong { color: #0EA5E9; font-weight: 800; margin-right: 4px; }

/* ── How it works ── */
.how-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 28px 0; }
.step-card {
    background: #1A1A24; border: 1px solid #2D3748; border-radius: 12px;
    padding: 28px 20px; text-align: center; transition: all 0.3s ease;
    position: relative; overflow: hidden;
}
.step-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: radial-gradient(circle at 50% 0%, rgba(14,165,233,0.06) 0%, transparent 70%);
    opacity: 0; transition: opacity 0.3s ease;
}
.step-card:hover {
    transform: translateY(-3px);
    border-color: #0EA5E9;
    box-shadow: 0 8px 32px rgba(14,165,233,0.12);
}
.step-card:hover::before { opacity: 1; }
.step-card .icon { font-size: 32px; margin-bottom: 10px; position: relative; }
.step-card h3 { font-size: 17px; font-weight: 700; color: #F8FAFC; margin-bottom: 6px; position: relative; }
.step-card p { font-size: 13px; color: #94A3B8; line-height: 1.5; margin: 0; position: relative; }

/* ── Category pills ── */
.cat-pills { display: flex; flex-wrap: wrap; gap: 10px; margin: 20px 0 32px 0; }

/* ── Listing grid ── */
.listing-grid { display: grid; gap: 16px; margin: 16px 0; }
.listing-grid-2 { grid-template-columns: repeat(2, 1fr); }
.listing-grid-3 { grid-template-columns: repeat(3, 1fr); }
.listing-grid-4 { grid-template-columns: repeat(4, 1fr); }

.card-link { text-decoration: none !important; color: inherit !important; }
.listing-card {
    background: #1A1A24;
    border: 1px solid #2D3748;
    border-radius: 10px;
    overflow: hidden;
    transition: all 0.25s ease;
    cursor: pointer;
}
.listing-card:hover {
    box-shadow: 0 4px 24px rgba(14,165,233,0.15);
    border-color: #0EA5E9;
    transform: translateY(-3px);
}

.card-img-wrap {
    position: relative;
    width: 100%;
    height: 200px;
    background: #111118;
    overflow: hidden;
}
.card-img-wrap::after {
    content: '';
    position: absolute; bottom: 0; left: 0; right: 0; height: 40px;
    background: linear-gradient(transparent, rgba(19,19,26,0.8));
    pointer-events: none;
}
.card-badge {
    position: absolute;
    top: 8px; left: 8px;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    color: white;
    z-index: 2;
}
.card-time-overlay {
    position: absolute;
    bottom: 8px; right: 8px;
    z-index: 2;
}
.card-body { padding: 12px 14px 14px 14px; }
.card-title {
    font-size: 14px;
    font-weight: 600;
    color: #F8FAFC;
    line-height: 1.35;
    margin-bottom: 4px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.card-location { font-size: 12px; color: #94A3B8; margin-bottom: 8px; }
.card-price-row { display: flex; align-items: baseline; justify-content: space-between; }
.card-price {
    font-size: 18px; font-weight: 700;
    background: linear-gradient(135deg, #84CC16, #22C55E);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.card-true-cost { font-size: 11px; color: #94A3B8; margin-top: 1px; }
.card-bids { font-size: 12px; color: #94A3B8; font-weight: 500; }
.card-time { font-size: 13px; color: white; background: rgba(255,255,255,0.15); padding: 5px 10px; border-radius: 6px; backdrop-filter: blur(4px); font-weight: 600; }
.card-time-urgent {
    font-size: 14px; color: white;
    background: linear-gradient(135deg, #EC4899, #F43F5E);
    padding: 5px 12px; border-radius: 6px; font-weight: 700;
    letter-spacing: 0.3px;
    box-shadow: 0 0 12px rgba(236,72,153,0.4);
    animation: pulseUrgent 2s ease-in-out infinite;
}

/* ── Section headers ── */
.sh { font-size: 24px; font-weight: 700; color: #F8FAFC; margin-bottom: 4px; }
.ss { font-size: 14px; color: #94A3B8; margin-bottom: 20px; }

/* ── Blog banners ── */
.blog-banner {
    display: flex; align-items: center; justify-content: center;
    border-radius: 10px 10px 0 0; font-size: 48px;
    position: relative; overflow: hidden;
}
.blog-banner::after {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: radial-gradient(circle at 70% 30%, rgba(255,255,255,0.15) 0%, transparent 60%);
    pointer-events: none;
}

/* ── Blog cards ── */
.blog-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }
.blog-card {
    background: #1A1A24; border: 1px solid #2D3748; border-radius: 10px;
    overflow: hidden; transition: all 0.25s ease;
}
.blog-card .blog-card-body { padding: 20px 24px 24px 24px; }
.blog-card:hover {
    box-shadow: 0 4px 24px rgba(168,85,247,0.15);
    border-color: #A855F7;
}
.blog-card .cat { font-size: 11px; font-weight: 700; color: #A855F7; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
.blog-card h3 { font-size: 16px; font-weight: 700; color: #F8FAFC; margin-bottom: 6px; line-height: 1.3; }
.blog-card .desc { font-size: 13px; color: #94A3B8; line-height: 1.5; margin-bottom: 10px; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.blog-card .date { font-size: 12px; color: #94A3B8; }

/* ── Blog article ── */
.article-header { margin-bottom: 28px; }
.article-header h1 { font-size: 30px; font-weight: 800; color: #F8FAFC; line-height: 1.2; margin-bottom: 8px; }
.article-header .meta { font-size: 13px; color: #94A3B8; }
.article-body { font-size: 16px; line-height: 1.8; color: #CBD5E1; max-width: 720px; }
.article-body h2 { font-size: 22px; font-weight: 700; color: #F8FAFC; margin-top: 28px; margin-bottom: 10px; }
.article-body h3 { font-size: 18px; font-weight: 600; color: #F8FAFC; margin-top: 20px; margin-bottom: 8px; }
.article-body a { color: #0EA5E9 !important; text-decoration: underline; text-underline-offset: 2px; }
.article-body table { width: 100%; border-collapse: collapse; margin: 16px 0; }
.article-body th, .article-body td { padding: 10px 14px; border: 1px solid #2D3748; text-align: left; color: #CBD5E1; }
.article-body th { background: #1A1A24; font-weight: 600; color: #F8FAFC; }
.article-body strong { color: #F8FAFC; }

/* ── Value section ── */
.value-section {
    background: #1A1A24; border: 1px solid #2D3748; border-radius: 12px; padding: 36px;
    text-align: center; margin: 36px 0; position: relative; overflow: hidden;
}
.value-section::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, #0EA5E9, #A855F7, transparent);
}
.value-section h2 { font-size: 26px; font-weight: 800; color: #F8FAFC; margin-bottom: 8px; }
.value-section p { font-size: 15px; color: #94A3B8; max-width: 500px; margin: 0 auto; }

/* ── Empty state ── */
.empty-state {
    text-align: center; padding: 60px 20px; color: #94A3B8;
}
.empty-state .icon { font-size: 56px; margin-bottom: 12px; opacity: 0.6; }
.empty-state h3 { font-size: 18px; font-weight: 600; color: #CBD5E1; margin-bottom: 4px; }
.empty-state p { font-size: 14px; color: #94A3B8; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #111118 !important;
    border-right: 1px solid #1E293B !important;
}
section[data-testid="stSidebar"] * { color: #CBD5E1 !important; }
section[data-testid="stSidebar"] hr { border-color: #2D3748 !important; }

/* Sidebar radio → styled nav pills */
section[data-testid="stSidebar"] [data-testid="stRadio"] > div { gap: 2px !important; }
section[data-testid="stSidebar"] [data-testid="stRadio"] > div[role="radiogroup"] { gap: 2px !important; }
section[data-testid="stSidebar"] [data-testid="stRadio"] label {
    display: flex !important; align-items: center !important;
    padding: 10px 14px !important; margin: 0 !important;
    border-radius: 8px !important; border: 1px solid transparent !important;
    background: transparent !important;
    color: #94A3B8 !important; font-size: 14px !important; font-weight: 500 !important;
    cursor: pointer !important; transition: all 0.15s ease !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: #1A1A24 !important; color: #F8FAFC !important;
    border-color: #2D3748 !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"],
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    background: linear-gradient(135deg, rgba(14,165,233,0.15), rgba(14,165,233,0.06)) !important;
    color: #0EA5E9 !important; font-weight: 600 !important;
    border-color: rgba(14,165,233,0.3) !important;
    box-shadow: 0 0 12px rgba(14,165,233,0.1) !important;
}
/* Hide the radio circle */
section[data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child {
    display: none !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label input[type="radio"] {
    display: none !important;
}

/* ── Misc ── */
.results-bar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; padding: 8px 0; border-bottom: 1px solid #1E293B; }
.results-count { font-size: 14px; color: #94A3B8; }
.results-count strong { color: #F8FAFC; }

/* ── Responsive ── */
@media (max-width: 768px) {
    .hero-compact { padding: 24px 20px 20px 20px; }
    .hero-compact h1 { font-size: 24px; }
    .hero-stats { flex-wrap: wrap; gap: 12px; }
    .how-grid { grid-template-columns: 1fr; }
    .listing-grid-3, .listing-grid-4 { grid-template-columns: repeat(2, 1fr); }
    .blog-grid { grid-template-columns: 1fr; }
}
@media (max-width: 480px) {
    .listing-grid-2, .listing-grid-3, .listing-grid-4 { grid-template-columns: 1fr; }
    .hero-compact h1 { font-size: 20px; }
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──
NAV_LABELS = {"Home": "\U0001F3E0  Home", "Search": "\U0001F50D  Search", "Ending Soon": "\u23F0  Ending Soon", "Saved Searches": "\U0001F516  Saved Searches", "Blog": "\U0001F4DD  Blog", "Settings": "\u2699\uFE0F  Settings"}

with st.sidebar:
    st.markdown('<div style="padding:8px 0 12px 0;"><span style="font-size:26px;">&#127963;</span> <span style="font-size:20px;font-weight:800;letter-spacing:-0.5px;color:white!important;vertical-align:middle;">GovGrab</span></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:12px;color:#94A3B8;margin-bottom:16px;">Government Surplus Auction Aggregator</div>', unsafe_allow_html=True)
    st.markdown("---")

    settings = load_settings()

    page = st.radio("Nav", PAGES, format_func=lambda p: NAV_LABELS.get(p, p), label_visibility="collapsed", key="_page_radio")

    st.markdown("---")
    st.markdown("**Platforms**")
    platforms = []
    if st.checkbox("GSA Auctions", value=True, help="Federal"):
        platforms.append("GSA Auctions")
    if st.checkbox("GovDeals", value=True, help="State/local (12.5% fee)"):
        platforms.append("GovDeals")
    if st.checkbox("PublicSurplus", value=True, help="State/local"):
        platforms.append("PublicSurplus")
    if st.checkbox("Municibid", value=True, help="Municipal (9% fee)"):
        platforms.append("Municibid")

    st.markdown("---")
    st.markdown('<div style="font-size:11px;color:#94A3B8;">GSA: No fee &middot; GovDeals: 12.5% &middot; PS: No fee &middot; Municibid: 9%</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# PAGE: Home
# ══════════════════════════════════════════════════════
if page == "Home":
    # Compact hero with inline search
    st.markdown(
        '<div class="hero-compact">'
        '<div class="hero-text">'
        '<h1>Stop Checking 5 Sites. Search <span class="hl">Once</span>.</h1>'
        '<p>Government surplus auctions from GSA, GovDeals, PublicSurplus &amp; Municibid in one search.</p>'
        '</div>'
        '<div class="hero-stats">'
        '<span class="hero-stat"><strong>4</strong> Platforms</span>'
        '<span class="hero-stat"><strong>100K+</strong> Listings</span>'
        '<span class="hero-stat"><strong>50</strong> States</span>'
        '<span class="hero-stat"><strong>$0</strong> To Start</span>'
        '</div>'
        '</div>', unsafe_allow_html=True)

    # Search bar
    qcol1, qcol2 = st.columns([4, 1])
    with qcol1:
        quick_search = st.text_input("quick_search", placeholder="Search auctions... e.g. Ford truck, laptop, excavator", label_visibility="collapsed")
    with qcol2:
        if st.button("Search", type="primary", use_container_width=True) or quick_search:
            if quick_search:
                st.session_state["_search_keyword"] = quick_search
                navigate_to("Search")
                st.rerun()

    # Category quick-filters
    cat_cols = st.columns(8)
    cat_labels = {
        "Vehicles": "\U0001F697", "Heavy Equipment": "\U0001F3D7\uFE0F",
        "Electronics & IT": "\U0001F4BB", "Office Furniture": "\U0001FA91",
        "Tools & Industrial": "\U0001F527", "Medical Equipment": "\U0001F3E5",
        "Real Estate & Land": "\U0001F3E0", "Agricultural": "\U0001F33E",
    }
    for i, (cat, emoji) in enumerate(cat_labels.items()):
        with cat_cols[i]:
            if st.button(f"{emoji} {cat.split(' &')[0].split(' ')[0]}", key=f"home_cat_{cat}", use_container_width=True):
                st.session_state["_search_category"] = cat
                navigate_to("Search")
                st.rerun()

    # Listings FIRST — immediately visible
    st.markdown('<div class="sh" style="margin-top:20px;">Live Auctions</div>', unsafe_allow_html=True)

    with st.spinner("Loading..."):
        preview = fetch_all_listings("", "All States", platforms, settings.get("gsa_api_key", ""))
    if preview:
        render_listing_grid(preview[:12], cols=4)
        st.markdown("")
        if st.button("See all listings  -->", type="primary"):
            navigate_to("Search")
            st.rerun()

    # How it works — below listings
    st.markdown("---")
    st.markdown('<div class="sh">How It Works</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="how-grid">'
        '<div class="step-card"><div class="icon">&#128269;</div><h3>1. Search Once</h3><p>One search spans GSA, GovDeals, PublicSurplus, and Municibid. Filter by state, category, and price.</p></div>'
        '<div class="step-card"><div class="icon">&#9878;&#65039;</div><h3>2. Compare Costs</h3><p>See the true cost including buyer&#39;s premiums. Different platforms charge different fees.</p></div>'
        '<div class="step-card"><div class="icon">&#128276;</div><h3>3. Save &amp; Alert</h3><p>Save searches and get alerted when new listings match. Never miss a deal again.</p></div>'
        '</div>', unsafe_allow_html=True)

    # Value prop
    st.markdown(
        '<div class="value-section">'
        '<h2>Built for Deal Hunters</h2>'
        '<p>Resellers, contractors, small businesses, and anyone who wants government surplus '
        'at 30-70% below retail. One search. All platforms.</p>'
        '</div>', unsafe_allow_html=True)

    # Blog teaser
    posts = load_blog_posts()
    if posts:
        st.markdown('<div class="sh">From the Blog</div>', unsafe_allow_html=True)
        blog_cols = st.columns(min(3, len(posts)))
        for i, post in enumerate(posts[:3]):
            with blog_cols[i]:
                st.markdown(
                    f'<div class="blog-card">'
                    f'{get_blog_banner_html(post["slug"])}'
                    f'<div class="blog-card-body">'
                    f'<div class="cat">{post["meta"].get("category", "Guide")}</div>'
                    f'<h3>{post["meta"].get("title", post["slug"])}</h3>'
                    f'<div class="desc">{post["meta"].get("description", "")[:120]}</div>'
                    f'<div class="date">{post["meta"].get("date", "")}</div>'
                    f'</div></div>', unsafe_allow_html=True)
                if st.button("Read", key=f"home_blog_{post['slug']}"):
                    st.session_state["blog_post"] = post["slug"]
                    navigate_to("Blog")
                    st.rerun()


# ══════════════════════════════════════════════════════
# PAGE: Search
# ══════════════════════════════════════════════════════
elif page == "Search":
    st.markdown('<div class="sh">Search Auctions</div>', unsafe_allow_html=True)

    # Pre-fill from navigation
    default_kw = st.session_state.pop("_search_keyword", "")
    default_cat = st.session_state.pop("_search_category", "All Categories")

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        keyword = st.text_input("Keyword", value=default_kw, placeholder="e.g., Ford truck, laptop, generator...", label_visibility="collapsed")
    with col2:
        state_filter = st.selectbox("State", US_STATES, label_visibility="collapsed")
    with col3:
        cat_idx = CATEGORIES.index(default_cat) if default_cat in CATEGORIES else 0
        category_filter = st.selectbox("Category", CATEGORIES, index=cat_idx, label_visibility="collapsed")

    col4, col5, col6, col7 = st.columns(4)
    with col4:
        min_price = st.number_input("Min Price ($)", min_value=0, value=0, step=50)
    with col5:
        max_price = st.number_input("Max Price ($)", min_value=0, value=0, step=500, help="0 = no limit")
    with col6:
        sort_by = st.selectbox("Sort By", ["Ending Soonest", "Price: Low to High", "Price: High to Low", "Most Bids"])
    with col7:
        view_cols = st.selectbox("View", ["3 columns", "2 columns", "4 columns"])

    if not platforms:
        st.warning("Select at least one platform in the sidebar.")
    else:
        with st.spinner("Searching across platforms..."):
            results = fetch_all_listings(keyword, state_filter, platforms, settings.get("gsa_api_key", ""))

        if category_filter != "All Categories":
            results = [r for r in results if r["category"] == category_filter]
        if min_price > 0:
            results = [r for r in results if r["current_bid"] is not None and r["current_bid"] >= min_price]
        if max_price > 0:
            results = [r for r in results if r["current_bid"] is not None and r["current_bid"] <= max_price]

        def sort_key(item):
            if sort_by == "Price: Low to High":
                return item["current_bid"] if item["current_bid"] is not None else float("inf")
            elif sort_by == "Price: High to Low":
                return -(item["current_bid"] if item["current_bid"] is not None else 0)
            elif sort_by == "Most Bids":
                return -(item["num_bids"] if item["num_bids"] is not None else 0)
            else:
                return item["end_date_dt"].timestamp() if item.get("end_date_dt") else float("inf")
        results.sort(key=sort_key)

        # Results bar
        platform_counts = {}
        for r in results:
            platform_counts[r["platform"]] = platform_counts.get(r["platform"], 0) + 1
        counts_str = " &middot; ".join([f"{p}: {c}" for p, c in platform_counts.items()])

        st.markdown(f'<div class="results-bar"><div class="results-count"><strong>{len(results)}</strong> results {f"&nbsp;&nbsp;({counts_str})" if counts_str else ""}</div></div>', unsafe_allow_html=True)

        # Save search
        c1, c2 = st.columns([1, 5])
        with c1:
            if st.button("Save search"):
                searches = load_saved_searches()
                searches.append({
                    "keyword": keyword, "state": state_filter, "category": category_filter,
                    "min_price": min_price, "max_price": max_price, "platforms": platforms,
                    "saved_at": datetime.now().isoformat(),
                })
                save_saved_searches(searches)
                st.success("Saved!")

        if not results:
            st.markdown(
                '<div class="empty-state">'
                '<div class="icon">&#128270;</div>'
                '<h3>No listings found</h3>'
                '<p>Try broadening your search or selecting more platforms.</p>'
                '</div>', unsafe_allow_html=True)
        else:
            # Pagination
            num_cols = int(view_cols.split()[0])
            per_page = num_cols * 6  # 6 rows
            total_pages = max(1, math.ceil(len(results) / per_page))
            if "search_page" not in st.session_state:
                st.session_state.search_page = 0
            cp = st.session_state.search_page
            if cp >= total_pages:
                cp = 0
                st.session_state.search_page = 0

            page_results = results[cp * per_page:(cp + 1) * per_page]
            render_listing_grid(page_results, cols=num_cols)

            # Pagination controls
            if total_pages > 1:
                p1, p2, p3 = st.columns([1, 3, 1])
                with p1:
                    if cp > 0 and st.button("< Previous"):
                        st.session_state.search_page = cp - 1
                        st.rerun()
                with p2:
                    st.markdown(f"<div style='text-align:center;color:#94A3B8;padding:8px;'>Page {cp+1} of {total_pages}</div>", unsafe_allow_html=True)
                with p3:
                    if cp < total_pages - 1 and st.button("Next >"):
                        st.session_state.search_page = cp + 1
                        st.rerun()


# ══════════════════════════════════════════════════════
# PAGE: Ending Soon
# ══════════════════════════════════════════════════════
elif page == "Ending Soon":
    st.markdown('<div class="sh">Ending Soon</div>', unsafe_allow_html=True)
    st.markdown('<div class="ss">Auctions closing in the next 24 hours</div>', unsafe_allow_html=True)

    if not platforms:
        st.warning("Select at least one platform.")
    else:
        with st.spinner("Loading..."):
            results = fetch_all_listings("", "All States", platforms, settings.get("gsa_api_key", ""))

        now = datetime.now()
        cutoff = now + timedelta(hours=24)
        ending_soon = []
        for r in results:
            if r.get("end_date_dt") and now < r["end_date_dt"] < cutoff:
                ending_soon.append(r)
            elif r.get("time_left"):
                tl = r["time_left"].lower()
                if "min" in tl or "hour" in tl:
                    ending_soon.append(r)
        ending_soon.sort(key=lambda x: x["end_date_dt"].timestamp() if x.get("end_date_dt") else float("inf"))

        st.markdown(f'<div class="results-bar"><div class="results-count"><strong>{len(ending_soon)}</strong> auctions ending soon</div></div>', unsafe_allow_html=True)

        if not ending_soon:
            st.markdown('<div class="empty-state"><div class="icon">&#9200;</div><h3>No auctions ending soon</h3><p>Check back later for last-minute deals.</p></div>', unsafe_allow_html=True)
        else:
            render_listing_grid(ending_soon[:24], cols=4)


# ══════════════════════════════════════════════════════
# PAGE: Saved Searches
# ══════════════════════════════════════════════════════
elif page == "Saved Searches":
    st.markdown('<div class="sh">Saved Searches</div>', unsafe_allow_html=True)
    st.markdown('<div class="ss">Your saved search alerts</div>', unsafe_allow_html=True)

    searches = load_saved_searches()

    if not searches:
        st.markdown('<div class="empty-state"><div class="icon">&#128278;</div><h3>No saved searches</h3><p>Search for something and click "Save search" to get started.</p></div>', unsafe_allow_html=True)
    else:
        for i, search in enumerate(searches):
            cols = st.columns([4, 1, 1])
            with cols[0]:
                parts = []
                if search.get("keyword"):
                    parts.append(f"**\"{search['keyword']}\"**")
                if search.get("state") and search["state"] != "All States":
                    parts.append(f"in {search['state']}")
                if search.get("category") and search["category"] != "All Categories":
                    parts.append(f"({search['category']})")
                st.markdown(" ".join(parts) if parts else "*All listings*")
                st.caption(f"Saved {search.get('saved_at', '')[:10]}")
            with cols[1]:
                if st.button("Run", key=f"run_{i}"):
                    st.session_state["_run_saved"] = search
                    st.rerun()
            with cols[2]:
                if st.button("Delete", key=f"del_{i}"):
                    searches.pop(i)
                    save_saved_searches(searches)
                    st.rerun()
            st.markdown("---")

    if "_run_saved" in st.session_state:
        search = st.session_state.pop("_run_saved")
        st.markdown("### Results")
        with st.spinner("Running..."):
            results = fetch_all_listings(search.get("keyword", ""), search.get("state", "All States"),
                                         search.get("platforms", platforms), settings.get("gsa_api_key", ""))
        if search.get("category") and search["category"] != "All Categories":
            results = [r for r in results if r["category"] == search["category"]]
        st.markdown(f'<div class="results-bar"><div class="results-count"><strong>{len(results)}</strong> results</div></div>', unsafe_allow_html=True)
        if results:
            render_listing_grid(results[:24], cols=3)


# ══════════════════════════════════════════════════════
# PAGE: Blog
# ══════════════════════════════════════════════════════
elif page == "Blog":
    posts = load_blog_posts()

    if "blog_post" in st.session_state:
        slug = st.session_state["blog_post"]
        post = next((p for p in posts if p["slug"] == slug), None)
        if post:
            if st.button("< Back to Blog"):
                del st.session_state["blog_post"]
                st.rerun()

            st.markdown(get_blog_banner_html(slug, height="200px"), unsafe_allow_html=True)
            st.markdown(
                f'<div class="article-header">'
                f'<div class="meta">{post["meta"].get("date", "")} &middot; {post["meta"].get("category", "")}</div>'
                f'<h1>{post["meta"].get("title", slug)}</h1>'
                f'<div class="meta">{post["meta"].get("description", "")}</div>'
                f'</div>', unsafe_allow_html=True)

            st.markdown(f'<div class="article-body">', unsafe_allow_html=True)
            st.markdown(post["body"])
            st.markdown('</div>', unsafe_allow_html=True)

            # Related posts
            others = [p for p in posts if p["slug"] != slug][:3]
            if others:
                st.markdown("---")
                st.markdown('<div class="sh">More Articles</div>', unsafe_allow_html=True)
                rcols = st.columns(min(3, len(others)))
                for i, op in enumerate(others):
                    with rcols[i]:
                        st.markdown(
                            f'<div class="blog-card">'
                            f'{get_blog_banner_html(op["slug"])}'
                            f'<div class="blog-card-body">'
                            f'<div class="cat">{op["meta"].get("category", "Guide")}</div>'
                            f'<h3>{op["meta"].get("title", op["slug"])}</h3>'
                            f'<div class="date">{op["meta"].get("date", "")}</div>'
                            f'</div></div>', unsafe_allow_html=True)
                        if st.button("Read", key=f"related_{op['slug']}"):
                            st.session_state["blog_post"] = op["slug"]
                            st.rerun()
        else:
            del st.session_state["blog_post"]
            st.rerun()
    else:
        st.markdown('<div class="sh">Blog</div>', unsafe_allow_html=True)
        st.markdown('<div class="ss">Tips, guides, and insights for government surplus buying</div>', unsafe_allow_html=True)

        if not posts:
            st.info("No blog posts yet. Add .md files to the blog/ directory.")
        else:
            blog_cols = st.columns(min(3, len(posts)))
            for i, post in enumerate(posts):
                with blog_cols[i % 3]:
                    st.markdown(
                        f'<div class="blog-card">'
                        f'{get_blog_banner_html(post["slug"])}'
                        f'<div class="blog-card-body">'
                        f'<div class="cat">{post["meta"].get("category", "General")}</div>'
                        f'<h3>{post["meta"].get("title", post["slug"])}</h3>'
                        f'<div class="desc">{post["meta"].get("description", "")[:150]}</div>'
                        f'<div class="date">{post["meta"].get("date", "")}</div>'
                        f'</div></div>', unsafe_allow_html=True)
                    if st.button("Read article", key=f"blog_{post['slug']}"):
                        st.session_state["blog_post"] = post["slug"]
                        st.rerun()


# ══════════════════════════════════════════════════════
# PAGE: Settings
# ══════════════════════════════════════════════════════
elif page == "Settings":
    st.markdown('<div class="sh">Settings</div>', unsafe_allow_html=True)

    st.markdown("#### GSA Auctions API Key")
    st.markdown("Get a **free** key from [api.data.gov/signup](https://api.data.gov/signup/) to enable federal surplus listings.")
    api_key = st.text_input("API Key", value=settings.get("gsa_api_key", ""), type="password")

    st.markdown("---")
    st.markdown("#### Location")
    zip_code = st.text_input("ZIP Code", value=settings.get("zip_code", ""))
    radius = st.slider("Radius (miles)", 25, 500, settings.get("radius_miles", 100), step=25)

    if st.button("Save Settings", type="primary"):
        settings["gsa_api_key"] = api_key
        settings["zip_code"] = zip_code
        settings["radius_miles"] = radius
        save_settings(settings)
        st.success("Saved!")
        st.cache_data.clear()

    st.markdown("---")
    st.markdown("#### Platform Fees")
    for name, info in PLATFORM_FEES.items():
        st.markdown(f"**{name}**: {info['buyer_premium']*100:.0f}% — {info['note']}")

    st.markdown("---")
    st.markdown("#### About")
    st.markdown("GovGrab aggregates government surplus auctions into one searchable interface. Currently: GSA, GovDeals, PublicSurplus, Municibid.")

# ── Footer (all pages) ──
st.markdown("---")
st.markdown(
    '<div style="text-align:center;padding:16px 0 8px 0;font-size:12px;color:#64748B;">'
    'GovGrab is not affiliated with, endorsed by, or connected to any government agency. '
    'Listing data is sourced from publicly available platforms.'
    '</div>', unsafe_allow_html=True)
