#!/usr/bin/env python3
"""Unit tests for Firecrawl lead discovery utilities."""
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from tools.firecrawl_leads import (
    parse_emails,
    parse_phones,
    normalize_company_size,
    filter_leads,
    dedupe_leads,
    validate_lead,
    build_query,
    normalize_exclusions,
)


class FirecrawlLeadTests(unittest.TestCase):
    def test_parse_emails(self):
        text = "Contact us at jane@company.com or sales@company.co.uk."
        self.assertEqual(sorted(parse_emails(text)), ["jane@company.com", "sales@company.co.uk"])

    def test_parse_phones(self):
        text = "Call +34 600 123 456 or +1 (415) 555-0101 for details."
        phones = parse_phones(text)
        self.assertIn("+34600123456", phones)
        self.assertIn("+14155550101", phones)

    def test_normalize_company_size(self):
        self.assertEqual(normalize_company_size(5), "1-10")
        self.assertEqual(normalize_company_size(25), "11-50")
        self.assertEqual(normalize_company_size(150), "51-200")
        self.assertEqual(normalize_company_size(500), "201-1000")
        self.assertEqual(normalize_company_size(5000), "1000+")

    def test_filter_leads(self):
        leads = [
            {
                "name": "Jane Doe",
                "role": "Head of Sales",
                "email": "jane@acme.com",
                "phone": "+34600123456",
                "company": "Acme",
                "region": "Spain",
                "industry": "SaaS",
                "company_size": "51-200",
                "source_url": "https://acme.com/about",
            },
            {
                "name": "Luis Perez",
                "role": "Founder",
                "email": "luis@beta.io",
                "phone": "+34900111222",
                "company": "Beta",
                "region": "UK",
                "industry": "Manufacturing",
                "company_size": "11-50",
                "source_url": "https://beta.io/team",
            },
        ]
        filtered = filter_leads(
            leads,
            region="Spain",
            industry="SaaS",
            company_size="51-200",
            employee_role="Head of Sales",
        )
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["name"], "Jane Doe")

    def test_filter_exclusions(self):
        leads = [
            {
                "name": "Owner",
                "role": "Owner",
                "email": "owner@boots.com",
                "phone": "+441234567890",
                "company": "Boots UK",
                "region": "UK",
                "industry": "Pharmacy",
                "company_size": "1000+",
                "source_url": "https://boots.com/contact",
            },
            {
                "name": "Owner",
                "role": "Owner",
                "email": "owner@independentpharmacy.co.uk",
                "phone": "+441111111111",
                "company": "Independent Pharmacy",
                "region": "UK",
                "industry": "Pharmacy",
                "company_size": "11-50",
                "source_url": "https://independentpharmacy.co.uk/about",
            },
        ]
        exclusions = normalize_exclusions("boots, lloyds")
        filtered = filter_leads(
            leads,
            region="UK",
            industry="Pharmacy",
            company_size=None,
            employee_role="Owner",
            exclude_companies=exclusions,
        )
        self.assertEqual(len(filtered), 1)
        self.assertIn("Independent", filtered[0]["company"])

    def test_dedupe_leads(self):
        leads = [
            {
                "name": "Jane Doe",
                "role": "Head of Sales",
                "email": "jane@acme.com",
                "phone": "+34600123456",
                "company": "Acme",
                "region": "Spain",
                "industry": "SaaS",
                "company_size": "51-200",
                "source_url": "https://acme.com/about",
            },
            {
                "name": "Jane Doe",
                "role": "Head of Sales",
                "email": "jane@acme.com",
                "phone": "+34600123456",
                "company": "Acme",
                "region": "Spain",
                "industry": "SaaS",
                "company_size": "51-200",
                "source_url": "https://acme.com/team",
            },
        ]
        deduped = dedupe_leads(leads)
        self.assertEqual(len(deduped), 1)

    def test_validate_lead(self):
        lead = {
            "name": "Jane Doe",
            "role": "Head of Sales",
            "email": "jane@acme.com",
            "phone": "+34600123456",
            "company": "Acme",
            "region": "Spain",
            "industry": "SaaS",
            "company_size": "51-200",
            "source_url": "https://acme.com/about",
        }
        self.assertTrue(validate_lead(lead))
        invalid = dict(lead)
        invalid["email"] = "bad-email"
        self.assertFalse(validate_lead(invalid))

    def test_build_query(self):
        query = build_query("Spain", "SaaS", "51-200", "Head of Sales")
        self.assertIn("Spain", query)
        self.assertIn("SaaS", query)
        self.assertIn("Head of Sales", query)


if __name__ == "__main__":
    unittest.main()
