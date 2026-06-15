"""
Engineering → Product Workflow (r21-25): Handoffs, swimlanes.
"""
from backend.core.handoff_queue import HandoffQueue
from backend.core.operating_ledger import OperatingLedger

class EngineeringToProduct:
    def __init__(self, ledger: OperatingLedger, queue: HandoffQueue):
        self.ledger = ledger
        self.queue = queue

    def handoff_pr(self, pr_id: str, artifacts: list) -> bool:
        return self.queue.create_handoff(
            ticket_id=pr_id,
            from_dept="engineering",
            to_dept="product",
            artifacts=artifacts
        )

if __name__ == "__main__":
    ledger = OperatingLedger()
    queue = HandoffQueue(ledger)
    workflow = EngineeringToProduct(ledger, queue)
    print("Engineering → Product workflow initialized (r21-25).")
