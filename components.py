"""GovGrab — Streamlit rendering components."""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from utils import compute_true_cost


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
            'width:100%;height:100%;background:#1A1A24;color:#475569;">'
            '<div style="text-align:center;"><div style="font-size:36px;opacity:0.5;">&#128247;</div>'
            '<div style="font-size:11px;margin-top:4px;color:#64748B;">No image</div></div></div>'
        )
    else:
        img_html = (
            '<div style="display:flex;align-items:center;justify-content:center;'
            'height:100%;background:#1A1A24;color:#475569;">'
            '<div style="text-align:center;"><div style="font-size:36px;opacity:0.5;">&#128247;</div>'
            '<div style="font-size:11px;margin-top:4px;color:#64748B;">No image</div></div></div>'
        )

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

    import html as html_mod
    safe_title = html_mod.escape(listing["title"]).replace("'", "\\'")
    price_val = listing["current_bid"] if listing["current_bid"] is not None else 0

    return (
        f'<a href="{listing["url"]}" target="_blank" class="card-link" '
        f'onclick="gg_listing_click(\'{listing["platform"]}\',\'{safe_title}\',{price_val})">'
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


def render_fee_banner():
    st.markdown(
        '<div class="fee-banner">'
        '<span class="fee-icon">&#128161;</span>'
        '<div>'
        '<strong>Watch the fees — the winning bid isn\'t always the final price.</strong><br>'
        '<div class="fee-chips">'
        '<span class="fee-chip">GSA: No fee</span>'
        '<span class="fee-chip">PublicSurplus: No fee</span>'
        '<span class="fee-chip">GovDeals: +12.5%</span>'
        '<span class="fee-chip">Municibid: +9%</span>'
        '</div>'
        '</div>'
        '</div>', unsafe_allow_html=True)


def render_listing_grid(listings, cols=3, show_true_cost=True):
    """Render a grid of listing cards."""
    if not listings:
        return
    html_cards = [render_listing_card(l, show_true_cost) for l in listings]
    grid_html = f'<div class="listing-grid listing-grid-{cols}">{"".join(html_cards)}</div>'
    st.markdown(grid_html, unsafe_allow_html=True)
