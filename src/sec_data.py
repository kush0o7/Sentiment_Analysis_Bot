from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote
import xml.etree.ElementTree as ET

import requests

DATA_DIR = Path("data")
SEC_CACHE_DIR = DATA_DIR / "sec_cache"
SEC_CACHE_DIR.mkdir(parents=True, exist_ok=True)

SEC_TICKERS_URLS = [
    "https://www.sec.gov/files/company_tickers.json",
    "https://www.sec.gov/files/company_tickers_exchange.json",
]
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_ARCHIVES = "https://data.sec.gov/Archives/edgar/data"


def _sec_headers() -> Dict[str, str]:
    agent = os.getenv("SEC_USER_AGENT")
    if not agent:
        raise RuntimeError(
            "SEC_USER_AGENT is required for SEC requests. "
            "Set it to something like 'SentimentAnalysisBot/1.0 you@email.com'."
        )
    return {"User-Agent": agent, "Accept-Encoding": "gzip, deflate"}


def _cache_read(path: Path, max_age_sec: int) -> Optional[Dict]:
    if not path.exists():
        return None
    if max_age_sec > 0:
        age = time.time() - path.stat().st_mtime
        if age > max_age_sec:
            return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _cache_write(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f)


def fetch_company_tickers(force: bool = False) -> Dict:
    cache_path = SEC_CACHE_DIR / "company_tickers.json"
    cached = None if force else _cache_read(cache_path, max_age_sec=7 * 24 * 3600)
    if cached:
        return cached
    last_err = None
    for url in SEC_TICKERS_URLS:
        try:
            resp = requests.get(url, headers=_sec_headers(), timeout=20)
            resp.raise_for_status()
            data = resp.json()
            _cache_write(cache_path, data)
            return data
        except Exception as exc:
            last_err = exc
            continue
    raise RuntimeError(f"Failed to fetch SEC ticker list: {last_err}")


def find_cik_by_ticker(ticker: str) -> Optional[str]:
    data = fetch_company_tickers()
    t = ticker.strip().upper()
    for _, entry in data.items():
        if entry.get("ticker", "").upper() == t:
            return str(entry.get("cik_str", "")).zfill(10)
    return None


def search_cik_by_name(name: str, limit: int = 5) -> List[Dict]:
    data = fetch_company_tickers()
    n = name.strip().lower()
    matches: List[Dict] = []
    for _, entry in data.items():
        title = str(entry.get("title", "")).lower()
        if n in title:
            matches.append(
                {
                    "cik": str(entry.get("cik_str", "")).zfill(10),
                    "title": entry.get("title"),
                    "ticker": entry.get("ticker"),
                }
            )
    return matches[:limit]


def fetch_submissions(cik: str, force: bool = False) -> Dict:
    cache_path = SEC_CACHE_DIR / f"submissions_{cik}.json"
    cached = None if force else _cache_read(cache_path, max_age_sec=12 * 3600)
    if cached:
        return cached
    url = SEC_SUBMISSIONS_URL.format(cik=cik)
    resp = requests.get(url, headers=_sec_headers(), timeout=20)
    resp.raise_for_status()
    data = resp.json()
    _cache_write(cache_path, data)
    return data


def _latest_filing(submissions: Dict, form_types: List[str]) -> Optional[Dict]:
    filings = submissions.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    accession = filings.get("accessionNumber", [])
    dates = filings.get("filingDate", [])
    docs = filings.get("primaryDocument", [])
    for idx, form in enumerate(forms):
        if form in form_types:
            return {
                "form": form,
                "accession": accession[idx],
                "filing_date": dates[idx],
                "primary_doc": docs[idx],
            }
    return None


def _filing_index(cik: str, accession: str) -> Dict:
    acc_no = accession.replace("-", "")
    url = f"{SEC_ARCHIVES}/{int(cik)}/{acc_no}/index.json"
    resp = requests.get(url, headers=_sec_headers(), timeout=20)
    resp.raise_for_status()
    return resp.json()


def _find_info_table_file(files: List[Dict]) -> Optional[str]:
    patterns = [
        re.compile(r".*infotable.*\.xml$", re.IGNORECASE),
        re.compile(r".*informationtable.*\.xml$", re.IGNORECASE),
        re.compile(r".*form13f.*\.xml$", re.IGNORECASE),
    ]
    for f in files:
        name = f.get("name", "")
        for pat in patterns:
            if pat.match(name):
                return name
    return None


def fetch_13f_holdings_by_cik(cik: str, max_rows: int = 50) -> Dict:
    submissions = fetch_submissions(cik)
    latest = _latest_filing(submissions, ["13F-HR", "13F-HR/A"])
    if not latest:
        return {"cik": cik, "holdings": [], "filing_date": None}

    index = _filing_index(cik, latest["accession"])
    files = index.get("directory", {}).get("item", [])
    info_file = _find_info_table_file(files)
    if not info_file:
        return {"cik": cik, "holdings": [], "filing_date": latest["filing_date"]}

    acc_no = latest["accession"].replace("-", "")
    info_url = f"{SEC_ARCHIVES}/{int(cik)}/{acc_no}/{quote(info_file)}"
    resp = requests.get(info_url, headers=_sec_headers(), timeout=20)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    ns = {"ns": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {}
    rows = []
    for info in root.findall(".//ns:infoTable", ns) if ns else root.findall(".//infoTable"):
        def _text(tag: str) -> str:
            node = info.find(f"ns:{tag}", ns) if ns else info.find(tag)
            return node.text.strip() if node is not None and node.text else ""

        rows.append(
            {
                "issuer": _text("nameOfIssuer"),
                "title": _text("titleOfClass"),
                "cusip": _text("cusip"),
                "value": _text("value"),
                "shares": _text("sshPrnamt"),
                "put_call": _text("putCall"),
                "investment_discretion": _text("investmentDiscretion"),
            }
        )
        if len(rows) >= max_rows:
            break

    return {
        "cik": cik,
        "filing_date": latest["filing_date"],
        "accession": latest["accession"],
        "holdings": rows,
    }


def fetch_form4_insiders_by_cik(cik: str, max_filings: int = 5) -> Dict:
    submissions = fetch_submissions(cik)
    filings = submissions.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    accession = filings.get("accessionNumber", [])
    dates = filings.get("filingDate", [])
    docs = filings.get("primaryDocument", [])
    out = []
    for idx, form in enumerate(forms):
        if form == "4":
            acc_no = accession[idx].replace("-", "")
            doc = docs[idx]
            url = f"{SEC_ARCHIVES}/{int(cik)}/{acc_no}/{quote(doc)}"
            out.append(
                {
                    "filing_date": dates[idx],
                    "accession": accession[idx],
                    "document": doc,
                    "url": url,
                }
            )
        if len(out) >= max_filings:
            break
    return {"cik": cik, "filings": out}
