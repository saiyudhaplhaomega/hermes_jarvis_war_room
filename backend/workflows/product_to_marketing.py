"""
Product → Marketing Workflow (r21-25): Handoffs, cost-aware routing.
"""
from backend.core.handoff_queue import HandoffQueue
from backend.core.operating_ledger import OperatingLedger

class ProductToMarketing:
    def __init__(self, ledger: OperatingLedger, queue: HandoffQueue):
        self.ledger = ledger
        self.queue = queue

    def handoff_feature(self, feature_id: str, cost_target: str, artifacts: list) -> bool:
        return self.queue.create_handoff(
            ticket_id=feature_id,
            from_dept="product",
            to_dept="marketing",
            artifacts=artifacts + [{"cost_target": cost_target}]
        )

if __name__ == "__main__":
    ledger = OperatingLedger()
    queue = HandoffQueue(ledger)
    workflow = ProductToMarketing(ledger, queue)
    print("Product → Marketing workflow initialized (r21-25).")
