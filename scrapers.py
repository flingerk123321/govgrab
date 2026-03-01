"""GovGrab — Platform scrapers for GSA, GovDeals, PublicSurplus, and Municibid."""
from __future__ import annotations

import logging
import os
import re
import subprocess
import time
from datetime import datetime, timedelta

import requests
import streamlit as st
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlencode

from utils import UA, detect_category, parse_price, parse_date

logger = logging.getLogger("govgrab")

# ── GovDeals kill switch ──
ENABLE_GOVDEALS = os.getenv("ENABLE_GOVDEALS", "true").lower() != "false"

# ── Circuit breaker state (in-memory, resets on app restart) ──
_govdeals_circuit = {"tripped": False, "tripped_at": None, "cooldown_hours": 1}


def _curl_get(url):
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "-A", UA, "--max-time", "15", url],
            capture_output=True, text=True, timeout=20,
        )
        if result.returncode == 0 and len(result.stdout) > 100:
            return result.stdout
    except Exception:
        logger.exception("curl request failed for %s", url)
    return None


@st.cache_data(ttl=600)
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
        items = data if isinstance(data, list) else data.get("Results", data.get("results", data.get("auctions", [])))
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
        logger.exception("GSA Auctions scraper failed")
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
                logger.exception("Failed to parse PublicSurplus item")
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
                logger.exception("Failed to parse Municibid item")
                continue
        if len(items) < 20:
            break
        time.sleep(0.5)
    return listings


GOVDEALS_API_URL = "https://maestro.lqdt1.com/search/list"
GOVDEALS_API_KEY = os.getenv("GOVDEALS_API_KEY", "")
GOVDEALS_IMG_BASE = "https://webassets.lqdt1.com/assets/photos/"


def _govdeals_is_available():
    """Check kill switch and circuit breaker. Returns (available, reason)."""
    if not ENABLE_GOVDEALS:
        return False, "GovDeals is disabled via ENABLE_GOVDEALS config"
    if not GOVDEALS_API_KEY:
        return False, "GovDeals API key not configured"
    cb = _govdeals_circuit
    if cb["tripped"] and cb["tripped_at"]:
        elapsed = datetime.now() - cb["tripped_at"]
        if elapsed < timedelta(hours=cb["cooldown_hours"]):
            remaining = cb["cooldown_hours"] * 60 - elapsed.seconds // 60
            return False, f"GovDeals temporarily disabled (rate limited, retrying in ~{remaining}min)"
        cb["tripped"] = False
        cb["tripped_at"] = None
        logger.info("GovDeals circuit breaker reset after cooldown")
    return True, ""


@st.cache_data(ttl=600)
def fetch_govdeals_listings(keyword="", state="", zip_code="", radius_miles=0, max_pages=3):
    """Fetch GovDeals listings via their public frontend API."""
    available, reason = _govdeals_is_available()
    if not available:
        logger.info("GovDeals skipped: %s", reason)
        return []
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
                "zipcode": zip_code or "",
                "proximityWithinDistance": radius_miles if zip_code else 0,
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
            if resp.status_code in (403, 429):
                logger.warning("GovDeals returned %d — tripping circuit breaker for %dh",
                               resp.status_code, _govdeals_circuit["cooldown_hours"])
                _govdeals_circuit["tripped"] = True
                _govdeals_circuit["tripped_at"] = datetime.now()
                break
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
        except Exception:
            logger.exception("GovDeals scraper failed on page %d", page_num)
            break
        time.sleep(0.5)
    return listings


def fetch_all_listings(keyword, state, platforms, gsa_api_key, zip_code="", radius_miles=0):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    all_listings = []
    errors = []
    futures = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        if "GSA Auctions" in platforms and gsa_api_key:
            futures[pool.submit(fetch_gsa_listings, gsa_api_key)] = "GSA Auctions"
        if "GovDeals" in platforms:
            available, reason = _govdeals_is_available()
            if available:
                futures[pool.submit(fetch_govdeals_listings, keyword, state, zip_code, radius_miles)] = "GovDeals"
            else:
                errors.append(f"GovDeals ({reason})")
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
                logger.exception("Platform %s failed during fetch", name)
                errors.append(name)
    return all_listings, errors
