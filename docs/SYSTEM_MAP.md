# Week 2: System Map (2026-06-12)

## Components

### Backend
- **Core**: operating_ledger.py, kpi_dashboard.py, handoff_queue.py, permissions_matrix.py.
- **Workflows**: engineering_to_product.py, product_to_marketing.py, marketing_to_sales.py.
- **Observability**: audit_log.py, observability_dashboard.py.

### Frontend
- **Components**: KPIDashboard.tsx, HandoffQueue.tsx, PermissionsMatrix.tsx.

### Cross-Cutting
- **r52 Ledger**: 10 entities, 6 views.
- **r53 KPIs**: 7 company KPIs.
- **r54 Handoffs**: SLA tracking.
- **r55 Permissions**: 4 levels, 5 AI-NEVER gates.

## Data Flow
1. **Engineering → Product**: PR → Handoff → Product Review → Swimlane Update.
2. **Product → Marketing**: Feature Brief → Handoff → Cost-Aware Routing → Campaign Launch.
3. **Marketing → Sales**: Lead → Handoff → Discord Multi-Guild → Deal Creation.

## Dependencies
- **MiniMax M3**: $0 (existing subscription).
- **Codex Pro**: $0 (existing subscription).
- **Claude Code Pro**: $0 (existing subscription).
- **Ollama/Nemotron**: $0 (self-hosted).

