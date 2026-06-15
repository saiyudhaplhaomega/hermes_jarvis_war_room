"""
Marketing → Sales Workflow (r21-25): Handoffs, multi-guild Discord.
"""
from backend.core.handoff_queue import HandoffQueue
from backend.core.operating_ledger import OperatingLedger

class MarketingToSales:
    def __init__(self, ledger: OperatingLedger, queue: HandoffQueue):
        self.ledger = ledger
        self.queue = queue

    def handoff_lead(self, lead_id: str, guild_id: str, artifacts: list) -> bool:
        return self.queue.create_handoff(
            ticket_id=lead_id,
            from_dept="marketing",
            to_dept="sales",
            artifacts=artifacts + [{"guild_id": guild_id}]
        )

if __name__ == "__main__":
    ledger = OperatingLedger()
    queue = HandoffQueue(ledger)
    workflow = MarketingToSales(ledger, queue)
    print("Marketing → Sales workflow initialized (r21-25).")
