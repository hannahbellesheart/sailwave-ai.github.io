# Internal Tools

## Firecrawl Lead Discovery

This tool discovers leads based on region, industry, company size, and employee role.

### Requirements
- `FIRECRAWL_API_KEY` must be set in the environment.

### Example
```bash
export FIRECRAWL_API_KEY="..."
python3 tools/firecrawl_leads.py \
  --region "Spain" \
  --industry "SaaS" \
  --company-size "51-200" \
  --employee-role "Head of Sales"
```

Outputs:
- `leads.json`
- `leads.csv`
