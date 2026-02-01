#!/usr/bin/env python3
"""Firecrawl-powered lead discovery helpers (internal-first)."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
from typing import Any, Callable, Dict, Iterable, List, Optional
from urllib import request

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def parse_emails(text: str) -> List[str]:
    return sorted(set(match.group(0) for match in EMAIL_RE.finditer(text or "")))


def parse_phones(text: str) -> List[str]:
    phones = set()
    for match in PHONE_RE.finditer(text or ""):
        raw = match.group(0).strip()
        digits = re.sub(r"\D", "", raw)
        if not digits:
            continue
        if raw.startswith("+"):
            phones.add(f"+{digits}")
        else:
            phones.add(digits)
    return sorted(phones)


def normalize_company_size(count: int) -> str:
    if count <= 10:
        return "1-10"
    if count <= 50:
        return "11-50"
    if count <= 200:
        return "51-200"
    if count <= 1000:
        return "201-1000"
    return "1000+"


def normalize_exclusions(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


def build_query(region: str, industry: str, company_size: str, employee_role: str) -> str:
    parts = []
    for value in (region, industry, employee_role, company_size):
        if value:
            parts.append(value)
    return " ".join(parts)


def filter_leads(
    leads: Iterable[Dict[str, str]],
    region: Optional[str] = None,
    industry: Optional[str] = None,
    company_size: Optional[str] = None,
    employee_role: Optional[str] = None,
    exclude_companies: Optional[List[str]] = None,
) -> List[Dict[str, str]]:
    results = []
    exclusions = exclude_companies or []
    for lead in leads:
        company = lead.get("company", "")
        if exclusions:
            company_lower = company.lower()
            if any(term in company_lower for term in exclusions):
                continue
        if region and region.lower() not in (lead.get("region", "").lower()):
            continue
        if industry and industry.lower() not in (lead.get("industry", "").lower()):
            continue
        if company_size and company_size != lead.get("company_size"):
            continue
        if employee_role and employee_role.lower() not in (lead.get("role", "").lower()):
            continue
        results.append(lead)
    return results


def dedupe_leads(leads: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    deduped = []
    for lead in leads:
        email = (lead.get("email") or "").lower()
        key = email or f"{lead.get('name','').lower()}|{lead.get('company','').lower()}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(lead)
    return deduped


def validate_lead(lead: Dict[str, str]) -> bool:
    name = lead.get("name", "").strip()
    company = lead.get("company", "").strip()
    email = lead.get("email", "").strip()
    phone = lead.get("phone", "").strip()
    if not name or not company:
        return False
    if email and not EMAIL_RE.fullmatch(email):
        return False
    if phone:
        digits = re.sub(r"\D", "", phone)
        if len(digits) < 7:
            return False
    return True


def _require_api_key() -> str:
    key = os.getenv("FIRECRAWL_API_KEY")
    if not key:
        raise RuntimeError("FIRECRAWL_API_KEY is required")
    return key


def _fetch_json(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    key = _require_api_key()
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    with request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def discover_leads(
    region: str,
    industry: str,
    company_size: str,
    employee_role: str,
    exclude_companies: Optional[List[str]] = None,
    fetcher: Callable[[str, Dict[str, Any]], Dict[str, Any]] = _fetch_json,
    rate_limit_sec: float = 0.5,
) -> List[Dict[str, str]]:
    query = build_query(region, industry, company_size, employee_role)
    search_payload = {"query": query, "limit": 20}
    search_data = fetcher("https://api.firecrawl.dev/v1/search", search_payload)
    urls = [item.get("url") for item in search_data.get("results", []) if item.get("url")]

    leads = []
    for url in urls:
        crawl_payload = {"url": url, "formats": ["markdown"]}
        page = fetcher("https://api.firecrawl.dev/v1/crawl", crawl_payload)
        content = page.get("data", "")
        emails = parse_emails(content)
        phones = parse_phones(content)
        for email in emails or [""]:
            lead = {
                "name": page.get("meta", {}).get("title", "").strip() or "Unknown",
                "role": employee_role,
                "email": email,
                "phone": phones[0] if phones else "",
                "company": page.get("meta", {}).get("site_name", "").strip() or "Unknown",
                "region": region,
                "industry": industry,
                "company_size": company_size,
                "source_url": url,
            }
            if validate_lead(lead):
                leads.append(lead)
        time.sleep(rate_limit_sec)

    return dedupe_leads(
        filter_leads(
            leads,
            region=region,
            industry=industry,
            company_size=company_size,
            employee_role=employee_role,
            exclude_companies=exclude_companies,
        )
    )


def export_json(leads: List[Dict[str, str]], path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(leads, handle, ensure_ascii=False, indent=2)


def export_csv(leads: List[Dict[str, str]], path: str) -> None:
    if not leads:
        return
    fieldnames = list(leads[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(leads)


def main() -> None:
    parser = argparse.ArgumentParser(description="Firecrawl lead discovery")
    parser.add_argument("--region", required=True)
    parser.add_argument("--industry", required=True)
    parser.add_argument("--company-size", required=True)
    parser.add_argument("--employee-role", required=True)
    parser.add_argument("--exclude-companies", default="", help="Comma-separated company names to exclude")
    parser.add_argument("--out-json", default="leads.json")
    parser.add_argument("--out-csv", default="leads.csv")
    args = parser.parse_args()

    leads = discover_leads(
        region=args.region,
        industry=args.industry,
        company_size=args.company_size,
        employee_role=args.employee_role,
        exclude_companies=normalize_exclusions(args.exclude_companies),
    )
    export_json(leads, args.out_json)
    export_csv(leads, args.out_csv)
    print(f"Exported {len(leads)} leads to {args.out_json} and {args.out_csv}")


if __name__ == "__main__":
    main()
