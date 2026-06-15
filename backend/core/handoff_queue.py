"""
Handoff Queue (r54): vw_handoff_queue, SLA tracking, dispute resolution.
"""
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List

from core.operating_ledger import OperatingLedger


# SLA hours per department pair (r54)
SLA_HOURS = {
    ("engineering", "product"): 48,
    ("product", "marketing"): 24,
    ("marketing", "sales"): 12,
    ("sales", "customer_success"): 24,
    ("customer_success", "product"): 48,
}


class HandoffQueue:
    def __init__(self, ledger: OperatingLedger):
        self.ledger = ledger

    def create_handoff(
        self,
        ticket_id: str,
        from_dept: str,
        to_dept: str,
        artifacts: List[Dict] = None,
    ) -> Dict:
        """Create a handoff, persist to ledger, return the handoff record."""
        artifacts = artifacts or []
        sla_deadline = self._calculate_sla_deadline(from_dept, to_dept)
        handoff = {
            "ticket_id": ticket_id,
            "from_dept": from_dept,
            "to_dept": to_dept,
            "artifacts": artifacts,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sla_deadline": sla_deadline,
        }
        self.ledger.write("handoff", ticket_id, handoff)
        return handoff

    def get_handoff(self, ticket_id: str) -> Dict | None:
        """Retrieve a handoff by ticket_id."""
        return self.ledger.query("handoff", ticket_id)

    def list_handoffs(self, status: str = None) -> List[Dict]:
        """List all handoffs, optionally filtered by status."""
        handoffs = self.ledger.query_view("vw_handoffs") if "vw_handoffs" in self.ledger.ALLOWED_VIEWS else []
        if status:
            handoffs = [h for h in handoffs if h.get("data", {}).get("status") == status]
        return handoffs

    def _calculate_sla_deadline(self, from_dept: str, to_dept: str) -> str:
        """Calculate SLA deadline based on department pair."""
        hours = SLA_HOURS.get((from_dept, to_dept), 72)  # default 72h
        deadline = datetime.now(timezone.utc) + timedelta(hours=hours)
        return deadline.isoformat()


if __name__ == "__main__":
    ledger = OperatingLedger()
    queue = HandoffQueue(ledger)
    print("Handoff Queue initialized (r54).")