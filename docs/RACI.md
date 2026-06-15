# Week 3: Owner/RACI (2026-06-12)

## RACI Matrix

| Task                          | Engineering | Product | Marketing | Sales | Finance-Ops | Security | Council |
|-------------------------------|-------------|---------|-----------|-------|-------------|----------|---------|
| operating_ledger.py           | R           | C       | C         | C     | A           | C        | I       |
| kpi_dashboard.py              | R           | C       | C         | C     | A           | C        | I       |
| handoff_queue.py              | R           | R       | R         | R     | C           | C        | A       |
| permissions_matrix.py         | R           | C       | C         | C     | C           | A        | I       |
| engineering_to_product.py     | R           | A       | C         | C     | C           | C        | I       |
| product_to_marketing.py       | C           | R       | A         | C     | C           | C        | I       |
| marketing_to_sales.py         | C           | C       | R         | A     | C           | C        | I       |
| audit_log.py                  | R           | C       | C         | C     | C           | A        | I       |
| observability_dashboard.py    | R           | C       | C         | C     | C           | A        | I       |

**Legend**:
- R = Responsible
- A = Accountable
- C = Consulted
- I = Informed

