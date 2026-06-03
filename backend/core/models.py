"""Pydantic models for NL router and API contracts."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class AgentStatus(BaseModel):
    name: str
    model: str
    tier: int = Field(ge=0, le=3)
    alive: bool
    current_task: Optional[str] = None
    score: float = 0.0
    cost_today: float = 0.0
    color: str = "#6b7280"

class TaskBrief(BaseModel):
    id: str
    name: str
    status: str
    phase: str
    agents: List[str] = []
    metrics: Dict[str, Any] = {}

class KanbanCard(BaseModel):
    id: str
    title: str
    status: str
    assignee: str
    priority: int
    last_heartbeat_at: Optional[str] = None

class DecisionItem(BaseModel):
    timestamp: str
    decision_id: str
    title: str
    status: str = "pending"
    confidence: float = 0.5
    approvers: List[str] = []

class MemoryStats(BaseModel):
    pending: int = 0
    approved: int = 0
    contradictions: int = 0
    per_agent_writes: Dict[str, int] = {}

class NLIntent(BaseModel):
    intent_type: str  # query | build | deploy | plan
    target: str       # dashboard | task | agent
    action: str       # show | create | deploy | edit
    tier: int = Field(ge=0, le=3)
    parameters: Dict[str, Any] = {}
    estimated_cost_usd: float = 0.0
    confirmation_required: bool = False

class NLResponse(BaseModel):
    intent: NLIntent
    response: str
    tier: int = 0
    confirmation_required: Optional[bool] = False
    estimated_cost: Optional[float] = None
    council_required: Optional[bool] = False

class MetricsSummary(BaseModel):
    tokens_today: int = 0
    cost_today: float = 0.0
    budget_remaining: float = 50.0

# Phase 2 additions-----------------------------------------------------------

class WSMessage(BaseModel):
    """Schema for WebSocket broadcast messages."""
    channel: str = "all"         # agents | kanban | memory | metrics | audit | transcripts | discord
    type: str = "snapshot"      # snapshot | event | toast
    payload: Dict[str, Any] = {}
    ts: str = ""

class AchievementDef(BaseModel):
    id: str
    name: str
    description: str
    category: str              # builder | scholar | commander | pioneer
    tier: int                  # 1=bronze, 2=silver, 3=gold
    icon: str                  # SVG path d attribute
    unlocked_at: Optional[str] = None

class SessionSummary(BaseModel):
    session_id: str
    title: str
    when: str                  # local date string
    message_count: int = 0
    source: str = "unknown"

class AuditRecord(BaseModel):
    ts: str
    severity: str              # info | warn | error
    category: str              # auth | dispatch | data | system
    action: str
    detail: str
    agent: Optional[str] = None

class DiscordThread(BaseModel):
    guild_id: str
    channel_id: str
    thread_id: str
    thread_name: str
    participant_bots: List[str] = []
    last_message_ts: Optional[str] = None
