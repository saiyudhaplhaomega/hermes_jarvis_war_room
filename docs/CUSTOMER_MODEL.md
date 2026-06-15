# Week 4: Canonical Customer Model (2026-06-12)

## Schema (r52)

### Account
```json
{
  "account_id": "str",
  "name": "str",
  "industry": "str",
  "mrr": "float",
  "arr": "float",
  "health_score": "int",
  "onboarding_status": "str",
  "renewal_date": "str",
  "csm": "str"
}
```

### Contact
```json
{
  "contact_id": "str",
  "account_id": "str",
  "name": "str",
  "email": "str",
  "role": "str",
  "last_contact_date": "str"
}
```

### Deal
```json
{
  "deal_id": "str",
  "account_id": "str",
  "amount": "float",
  "stage": "str",
  "close_date": "str",
  "probability": "float"
}
```

## Views (r52)
1. `vw_accounts`: All accounts.
2. `vw_contacts`: All contacts.
3. `vw_deals`: All deals.
4. `vw_health_scores`: Account health scores.
5. `vw_renewals`: Upcoming renewals.
6. `vw_mrr_trends`: MRR trends.

