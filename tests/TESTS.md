# Test Inventory

Update this document whenever a new test is created.

## tests/firecrawl_leads_tests.py

**Purpose:** Validate Firecrawl lead discovery helpers (parsing, filtering, dedupe, validation).

**Coverage**
- `tools/firecrawl_leads.py`: email/phone parsing, company size normalization, filters, dedupe rules, lead validation, query builder.

**How to run**
```bash
python3 tests/firecrawl_leads_tests.py
```
