"""
Custom provider example
------------------------
Template for a one-off county site that doesn't run any shared platform --
e.g. a results page you have to scrape directly (HTML table, PDF, whatever
that county happens to publish). Every custom county gets its OWN small
module like this one; copy this file and adjust `_normalize` and the fetch
logic.

Uses BeautifulSoup for HTML parsing -- add `beautifulsoup4` to
requirements.txt if you go this route for a given county.
"""

import requests
from bs4 import BeautifulSoup


def fetch_county(county_key, provider_config):
    """
    provider_config comes from registry.py, e.g.:
        {
            "url": "https://weirdcounty.gov/elections/results.html"
        }
    """

    response = requests.get(provider_config["url"], timeout=10)
    response.raise_for_status()

    return _normalize(response.text)


def _normalize(html):

    soup = BeautifulSoup(html, "html.parser")

    # TODO: this is a placeholder scrape -- adjust selectors to match
    # the real page. The example below assumes a table like:
    #
    #   <table id="results">
    #     <tr><td>Victor Marx</td><td>Republican</td><td>12,345</td></tr>
    #     ...
    #   </table>

    candidates = []

    table = soup.find("table", id="results")

    if table:
        for row in table.find_all("tr")[1:]:  # skip header row
            cells = row.find_all("td")

            if len(cells) < 3:
                continue

            name = cells[0].get_text(strip=True)
            party = cells[1].get_text(strip=True) or None
            votes_text = cells[2].get_text(strip=True).replace(",", "")

            candidates.append({
                "name": name,
                "votes": int(votes_text) if votes_text.isdigit() else 0,
                "party": party,
                "color": None
            })

    # TODO: pull the real reporting percentage if the page has one
    percent_reporting = None

    return {
        "name": None,  # filled in from registry.py's county name
        "percent_reporting": percent_reporting,
        "candidates": candidates
    }
