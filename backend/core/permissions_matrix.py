"""
Permissions Matrix (r55): 4 levels (AUTO/APPROVE/HUMAN/NONE), 5 AI-NEVER gates.
"""
from enum import Enum


class PermissionLevel(Enum):
    AUTO = 1      # No human approval
    APPROVE = 2   # Human approval required
    HUMAN = 3     # Human-only
    NONE = 4      # No access


class PermissionsMatrix:
    def __init__(self):
        self.matrix = {
            "engineering": {
                "deploy_prod": PermissionLevel.APPROVE,
                "merge_pr": PermissionLevel.AUTO,
                "access_finance": PermissionLevel.NONE,
            },
            "product": {
                "edit_roadmap": PermissionLevel.APPROVE,
                "create_handoff": PermissionLevel.AUTO,
                "access_security": PermissionLevel.NONE,
            },
            "marketing": {
                "launch_campaign": PermissionLevel.APPROVE,
                "create_lead": PermissionLevel.AUTO,
            },
            "sales": {
                "close_deal": PermissionLevel.APPROVE,
                "create_quote": PermissionLevel.AUTO,
            },
            "customer_success": {
                "send_qbr": PermissionLevel.AUTO,
                "create_ticket": PermissionLevel.AUTO,
            },
            "finance_ops": {
                "approve_invoice": PermissionLevel.APPROVE,
                "view_payroll": PermissionLevel.HUMAN,
            },
            "security": {
                "revoke_access": PermissionLevel.APPROVE,
                "view_audit_log": PermissionLevel.AUTO,
            },
        }
        # 5 AI-NEVER gates per r55 spec: contract signing, refunds/credits,
        # employment changes, public statements, pricing exceptions.
        # Plus 5 additional PII/security gates for the implementation.
        self.ai_never = [
            "sign_contract",          # r55 spec: contract signing
            "issue_refund_credit",    # r55 spec: refunds/credits above threshold
            "hire_fire",              # r55 spec: employment changes
            "public_statement",       # r55 spec: public statements
            "pricing_exception",      # r55 spec: pricing exceptions
            "sign_contracts",         # legacy alias
            "access_payroll",         # impl: payroll access
            "access_legal_privileged",# impl: legal privileged info
            "access_customer_pii",    # impl: customer PII
            "delete_audit_log",       # impl: audit log integrity
        ]

    def check_permission(self, dept: str, action: str) -> PermissionLevel:
        """Check permission for a dept/action pair.

        AI-NEVER actions are always denied (NONE) regardless of dept.
        Unknown actions are denied (NONE).
        """
        if action in self.ai_never:
            return PermissionLevel.NONE
        return self.matrix.get(dept, {}).get(action, PermissionLevel.NONE)


if __name__ == "__main__":
    matrix = PermissionsMatrix()
    print("Permissions Matrix initialized (r55). AI-NEVER gates:", matrix.ai_never)