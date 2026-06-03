"""Natural language router -- Tier 0-3 dispatch gates with auth + audit."""
from fastapi import APIRouter, Depends
from core.models import NLResponse, NLIntent
from core.audit import log_action
from auth.dependencies import get_current_user
import random

router = APIRouter()

@router.post("/nl-router")
def nl_router(message: str, user: str = Depends(get_current_user)):
    intent = _parse_intent(message)
    log_action(user, "query", "nl-router", {"message": message[:80], "tier": intent.tier})
    if intent.tier == 0:
        return {"response": "Sure -- here is the current fleet status.", "tier": 0}
    elif intent.tier == 1:
        return {"response": 'I will create a task for "' + message + '". Assign to ' + intent.parameters.get("assignee", "jarvis-manager") + '?', "tier": 1, "confirmation_required": True}
    elif intent.tier == 2:
        cost = round(random.uniform(0.5, 2.5), 2)
        return {"response": f"This requires a build (Tier 2). Estimated cost: ${cost}. Proceed?", "tier": 2, "estimated_cost": cost, "confirmation_required": True}
    elif intent.tier == 3:
        cost = round(random.uniform(2.0, 5.0), 2)
        return {"response": f"This requires Boss review (Tier 3). Estimated cost: ${cost}. Council gate required. Proceed?", "tier": 3, "estimated_cost": cost, "confirmation_required": True, "council_required": True}
    return NLResponse(intent=intent, response="I did not understand that.")

def _parse_intent(message: str) -> NLIntent:
    msg = message.lower()
    if any(x in msg for x in ["show", "list", "status", "what is", "who is", "where"]):
        return NLIntent(intent_type="query", target="dashboard", action="show", tier=0, parameters={}, estimated_cost_usd=0.0, confirmation_required=False)
    if any(x in msg for x in ["deploy", "serve", "internet", "public", "production"]):
        return NLIntent(intent_type="deploy", target="dashboard", action="deploy", tier=3, parameters={}, estimated_cost_usd=3.0, confirmation_required=True)
    if any(x in msg for x in ["build", "create", "make", "add", "implement", "code"]):
        return NLIntent(intent_type="build", target="dashboard", action="create", tier=2, parameters={}, estimated_cost_usd=1.5, confirmation_required=True)
    return NLIntent(intent_type="plan", target="task", action="create", tier=1, parameters={}, estimated_cost_usd=0.5, confirmation_required=False)
