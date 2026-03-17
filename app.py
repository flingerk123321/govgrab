#!/usr/bin/env python3
"""GovGrab — Government Surplus Auction Aggregator
Aggregates listings from GSA Auctions, GovDeals, PublicSurplus, and Municibid.
"""
from __future__ import annotations

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not needed on Streamlit Cloud

import logging
import math
from datetime import datetime, timedelta

import streamlit as st

from utils import (
    CATEGORIES, PLATFORM_FEES, US_STATES,
    get_blog_banner_html, load_blog_posts, load_saved_searches, load_settings,
    sanitize_keyword, save_saved_searches, save_settings,
    get_blog_internal_links, get_structured_data_json, generate_sitemap_xml,
)
from scrapers import fetch_all_listings
from components import render_fee_banner, render_listing_grid
from styles import CSS, GA_SCRIPT

SITE_URL = "https://govgrab.net"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("govgrab")


# ── Navigation helper ──
def navigate_to(page_name, **kwargs):
    """Navigate to a page and pass params via session state."""
    st.session_state["_nav_page"] = page_name
    for k, v in kwargs.items():
        st.session_state[k] = v


# ══════════════════════════════════════════════════════
# STREAMLIT APP
# ══════════════════════════════════════════════════════
st.set_page_config(page_title="GovGrab", page_icon="https://em-content.zobj.net/source/twitter/376/classical-building_1f3db-fe0f.png", layout="wide", initial_sidebar_state="auto")

# ── Handle navigation from session state ──
PAGES = ["Home", "Search", "Ending Soon", "Saved Searches", "Blog", "Settings"]
if "_nav_page" in st.session_state:
    nav_target = st.session_state.pop("_nav_page")
    if nav_target in PAGES:
        st.session_state["_page_radio"] = nav_target

# ── Analytics & Global CSS ──
st.markdown(GA_SCRIPT, unsafe_allow_html=True)
st.markdown(CSS, unsafe_allow_html=True)

# ── Dynamic meta tags helper ──
def inject_meta_tags(title="GovGrab — Government Surplus Auction Search",
                     description="Search GSA Auctions, GovDeals, PublicSurplus & Municibid in one place. Find government surplus at 30-70% below retail.",
                     url=SITE_URL, og_type="website"):
    """Inject OpenGraph, Twitter Card, and SEO meta tags."""
    import html
    t = html.escape(title)
    d = html.escape(description)
    st.markdown(
        f'<meta property="og:title" content="{t}">'
        f'<meta property="og:description" content="{d}">'
        f'<meta property="og:type" content="{og_type}">'
        f'<meta property="og:url" content="{html.escape(url)}">'
        f'<meta name="twitter:card" content="summary">'
        f'<meta name="twitter:title" content="{t}">'
        f'<meta name="twitter:description" content="{d}">'
        f'<meta name="description" content="{d}">'
        f'<link rel="canonical" href="{html.escape(url)}">',
        unsafe_allow_html=True,
    )

# Google Search Console verification
st.markdown('<meta name="google-site-verification" content="fkt1BaAq8op9LLTznw8fqBMj2iJkEM7Y-3ZbdFecquw" />', unsafe_allow_html=True)

# Default meta tags (overridden per-page below)
inject_meta_tags()

# Structured data (JSON-LD) for search engines
st.markdown(get_structured_data_json(), unsafe_allow_html=True)


def render_email_capture():
    """Render an email signup CTA section."""
    st.markdown(
        '<div class="email-capture">'
        '<h3>Get Notified About New Deals</h3>'
        '<p>Enter your email to receive alerts when new auctions match popular searches.</p>'
        '</div>', unsafe_allow_html=True)
    ec1, ec2, ec3 = st.columns([2, 3, 2])
    with ec2:
        email_val = st.text_input("email_capture", placeholder="you@example.com", label_visibility="collapsed", key="email_capture_input")
        if st.button("Subscribe", key="email_subscribe_btn", type="primary", use_container_width=True):
            if email_val and "@" in email_val:
                # Store emails in a local file for now
                import os, json
                from utils import APP_DIR
                email_file = os.path.join(APP_DIR, "email_subscribers.json")
                emails = []
                if os.path.exists(email_file):
                    with open(email_file) as f:
                        emails = json.load(f)
                if email_val not in emails:
                    emails.append(email_val)
                    with open(email_file, "w") as f:
                        json.dump(emails, f, indent=2)
                st.success("You're subscribed! We'll email you when we launch alerts.")
                st.markdown('<script>gg_email_signup();</script>', unsafe_allow_html=True)
            else:
                st.warning("Please enter a valid email address.")


def render_share_buttons(title, url, content_type="page"):
    """Render social share buttons for a page or blog post."""
    import urllib.parse
    encoded_title = urllib.parse.quote(title)
    encoded_url = urllib.parse.quote(url)
    st.markdown(
        f'<div class="share-row">'
        f'<span style="font-size:13px;color:#94A3B8;font-weight:500;">Share:</span>'
        f'<a class="share-btn share-btn-x" href="https://twitter.com/intent/tweet?text={encoded_title}&url={encoded_url}" target="_blank" '
        f'onclick="gg_share(\'twitter\',\'{content_type}\',\'{url}\')">X</a>'
        f'<a class="share-btn share-btn-reddit" href="https://reddit.com/submit?url={encoded_url}&title={encoded_title}" target="_blank" '
        f'onclick="gg_share(\'reddit\',\'{content_type}\',\'{url}\')">Reddit</a>'
        f'<a class="share-btn share-btn-fb" href="https://www.facebook.com/sharer/sharer.php?u={encoded_url}" target="_blank" '
        f'onclick="gg_share(\'facebook\',\'{content_type}\',\'{url}\')">Facebook</a>'
        f'<a class="share-btn share-btn-linkedin" href="https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}" target="_blank" '
        f'onclick="gg_share(\'linkedin\',\'{content_type}\',\'{url}\')">LinkedIn</a>'
        f'</div>', unsafe_allow_html=True)


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


# ── Helper: per-platform "no results" feedback ──
def show_platform_status(results, errors, selected_platforms):
    """Show per-platform status badges so users know which sources returned nothing."""
    if errors:
        st.warning(f"Some platforms are temporarily unavailable: {', '.join(errors)}")
    platform_counts = {}
    for r in results:
        platform_counts[r["platform"]] = platform_counts.get(r["platform"], 0) + 1
    badges = []
    for p in selected_platforms:
        matched_error = next((e for e in errors if p in e), None)
        if matched_error:
            badges.append(f'<span class="platform-status platform-status-error">{p}: unavailable</span>')
        elif platform_counts.get(p, 0) == 0:
            badges.append(f'<span class="platform-status platform-status-empty">{p}: no results</span>')
        else:
            badges.append(f'<span class="platform-status platform-status-ok">{p}: {platform_counts[p]}</span>')
    st.markdown(" ".join(badges), unsafe_allow_html=True)


# ── Location settings for GovDeals ──
zip_code = settings.get("zip_code", "")
radius_miles = settings.get("radius_miles", 0)


# ══════════════════════════════════════════════════════
# PAGE: Home
# ══════════════════════════════════════════════════════
if page == "Home":
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
                st.session_state["_search_keyword"] = sanitize_keyword(quick_search)
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
    render_fee_banner()

    with st.spinner("Loading..."):
        preview, _home_errors = fetch_all_listings("", "All States", platforms, settings.get("gsa_api_key", ""), zip_code, radius_miles)
    if _home_errors:
        st.warning(f"Some platforms are temporarily unavailable: {', '.join(_home_errors)}")
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
        '<div class="step-card"><div class="icon">&#128278;</div><h3>3. Save</h3><p>Save your favorite searches and re-run them anytime with one click.</p></div>'
        '</div>', unsafe_allow_html=True)

    # Value prop
    st.markdown(
        '<div class="value-section">'
        '<h2>Built for Deal Hunters</h2>'
        '<p>Resellers, contractors, small businesses, and anyone who wants government surplus '
        'at 30-70% below retail. One search. All platforms.</p>'
        '</div>', unsafe_allow_html=True)

    # Email capture
    render_email_capture()

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
        keyword = sanitize_keyword(st.text_input("Keyword", value=default_kw, placeholder="e.g., Ford truck, laptop, generator...", label_visibility="collapsed"))
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
            results, search_errors = fetch_all_listings(keyword, state_filter, platforms, settings.get("gsa_api_key", ""), zip_code, radius_miles)

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

        # Fire GA4 search event
        st.markdown(f'<script>gg_search("{keyword}", "{state_filter}", "{category_filter}", {len(results)});</script>', unsafe_allow_html=True)

        # Results bar with per-platform status
        st.markdown(f'<div class="results-bar"><div class="results-count"><strong>{len(results)}</strong> results</div></div>', unsafe_allow_html=True)
        show_platform_status(results, search_errors, platforms)
        render_fee_banner()

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
            results, ending_errors = fetch_all_listings("", "All States", platforms, settings.get("gsa_api_key", ""), zip_code, radius_miles)

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
        show_platform_status(results, ending_errors, platforms)
        render_fee_banner()

        if not ending_soon:
            st.markdown('<div class="empty-state"><div class="icon">&#9200;</div><h3>No auctions ending soon</h3><p>Check back later for last-minute deals.</p></div>', unsafe_allow_html=True)
        else:
            render_listing_grid(ending_soon[:24], cols=4)


# ══════════════════════════════════════════════════════
# PAGE: Saved Searches
# ══════════════════════════════════════════════════════
elif page == "Saved Searches":
    st.markdown('<div class="sh">Saved Searches</div>', unsafe_allow_html=True)
    st.markdown('<div class="ss">Your saved search filters</div>', unsafe_allow_html=True)

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
            results, saved_errors = fetch_all_listings(search.get("keyword", ""), search.get("state", "All States"),
                                         search.get("platforms", platforms), settings.get("gsa_api_key", ""), zip_code, radius_miles)
        if saved_errors:
            st.warning(f"Some platforms are temporarily unavailable: {', '.join(saved_errors)}")
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
            post_title = post["meta"].get("title", slug)
            post_desc = post["meta"].get("description", "")
            post_url = f"{SITE_URL}/?blog={slug}"

            # Dynamic meta tags for this blog post
            inject_meta_tags(title=f"{post_title} — GovGrab", description=post_desc, url=post_url, og_type="article")
            st.markdown(get_structured_data_json(page_type="article", title=post_title, description=post_desc, url=post_url), unsafe_allow_html=True)

            # GA4 blog read event
            import html as html_mod
            st.markdown(f'<script>gg_blog_read("{slug}", "{html_mod.escape(post_title)}");</script>', unsafe_allow_html=True)

            if st.button("< Back to Blog"):
                del st.session_state["blog_post"]
                st.rerun()

            st.markdown(get_blog_banner_html(slug, height="200px"), unsafe_allow_html=True)
            st.markdown(
                f'<div class="article-header">'
                f'<div class="meta">{post["meta"].get("date", "")} &middot; {post["meta"].get("category", "")}</div>'
                f'<h1>{post_title}</h1>'
                f'<div class="meta">{post_desc}</div>'
                f'</div>', unsafe_allow_html=True)

            # Share buttons
            render_share_buttons(post_title, post_url, content_type="blog_post")

            # Render blog body with internal links appended
            internal_links_html = get_blog_internal_links(slug, posts)
            st.markdown(f'<div class="article-body">', unsafe_allow_html=True)
            st.markdown(post["body"])
            if internal_links_html:
                st.markdown(internal_links_html, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # CTA at end of each blog post
            st.markdown(
                '<div class="blog-cta">'
                '<h3>Search Government Auctions Now</h3>'
                '<p>Find vehicles, equipment, electronics, and more from GSA, GovDeals, PublicSurplus, and Municibid — all in one search.</p>'
                '<a href="/" onclick="return false;" id="blog-cta-link">Search on GovGrab</a>'
                '</div>', unsafe_allow_html=True)
            if st.button("Search auctions now", key="blog_cta_search"):
                navigate_to("Search")
                st.rerun()

            # Email capture after CTA
            render_email_capture()

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

    st.markdown("#### Location")
    new_zip = st.text_input("ZIP Code", value=settings.get("zip_code", ""))
    new_radius = st.slider("Radius (miles)", 25, 500, settings.get("radius_miles", 100), step=25)

    if st.button("Save Settings", type="primary"):
        settings["zip_code"] = new_zip
        settings["radius_miles"] = new_radius
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

# ── Footer with disclaimer (all pages) ──
st.markdown("---")
st.markdown(
    '<div style="text-align:center;padding:16px 0 8px 0;font-size:12px;color:#64748B;max-width:700px;margin:0 auto;line-height:1.6;">'
    'GovGrab is an independent search tool and is not affiliated with, endorsed by, or connected to '
    'GSA, GovDeals, PublicSurplus, Municibid, or any government agency. '
    'All listings and images are property of their respective owners. '
    'Click through to bid on the original site.'
    '</div>', unsafe_allow_html=True)
