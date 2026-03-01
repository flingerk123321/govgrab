# GovGrab

Government surplus auction aggregator. Search GSA Auctions, GovDeals, PublicSurplus, and Municibid from one interface.

![Screenshot placeholder](screenshot.png)

## Features

- **Unified search** across 4 government auction platforms
- **True cost display** — see prices including buyer's premiums
- **Ending Soon** — catch last-minute deals closing in 24 hours
- **Saved Searches** — save and re-run your favorite filters
- **Blog** — guides and tips for government surplus buying
- **Location filtering** — ZIP code + radius for GovDeals results

## Setup

### Prerequisites

- Python 3.9+
- [curl](https://curl.se/) (for PublicSurplus and Municibid scraping)

### Install

```bash
git clone <repo-url>
cd govt_auction_aggregator
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file:

```env
GSA_API_KEY=your_gsa_api_key_here
GOVDEALS_API_KEY=your_govdeals_api_key_here
```

| Variable | Required | Description |
|---|---|---|
| `GSA_API_KEY` | Yes | API key from [api.data.gov](https://api.data.gov/signup/) for GSA Auctions |
| `GOVDEALS_API_KEY` | Yes | GovDeals frontend API key |

### Run

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## Project Structure

```
app.py          — Streamlit app orchestrator (pages, sidebar, routing)
scrapers.py     — Platform fetch functions (GSA, GovDeals, PublicSurplus, Municibid)
utils.py        — Helpers: config, parsing, blog, settings, categories
components.py   — UI rendering (listing cards, grids, fee banner)
styles.py       — All CSS as a single constant
blog/           — Markdown blog posts with YAML frontmatter
```

## Docker

```bash
docker build -t govgrab .
docker run -p 8501:8501 --env-file .env govgrab
```

## Deployment

Works on any platform that runs Docker or Python:

- **Streamlit Cloud** — connect your repo, set env vars in dashboard
- **Railway / Render** — deploy from Dockerfile
- **Fly.io** — `fly launch`, set secrets with `fly secrets set`

## License

MIT
