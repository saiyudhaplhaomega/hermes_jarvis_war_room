"""Read-only cache endpoints with project filtering, audit trail and auth dependency."""
from fastapi import APIRouter, Depends, Query
from core.audit import log_action
from auth.dependencies import get_current_user
import json
from copy import deepcopy
from core.config import CACHE_FILE

router = APIRouter()

def _normal_project(project) -> str:
    return project if isinstance(project, str) else ""

def _matches_project(item: dict, project: str) -> bool:
    project = _normal_project(project)
    if not project:
        return True
    if not isinstance(item, dict):
        return False
    haystack = " ".join(str(item.get(k, "")) for k in ("project", "id", "title", "source", "key"))
    return project in haystack

def _filter_cache_for_project(cache: dict, project: str) -> dict:
    project = _normal_project(project)
    if not project:
        return cache
    scoped = deepcopy(cache)
    scoped["active_project"] = project
    kb = scoped.get("kanban_by_project", {}) or {}
    scoped["kanban_by_project"] = {project: kb.get(project, [])}
    scoped["tasks"] = [t for t in scoped.get("tasks", []) if _matches_project(t, project)]
    scoped["decisions"] = [d for d in scoped.get("decisions", []) if _matches_project(d, project)]
    memory = scoped.get("memory", {}) or {}
    scoped["memory"] = {k: v for k, v in memory.items() if _matches_project(v, project)}
    sessions = scoped.get("sessions", []) or []
    scoped["sessions"] = [s for s in sessions if _matches_project(s, project)]
    return scoped

@router.get("/cache")
def get_cache(project: str = Query(""), user: str = Depends(get_current_user)):
    log_action(user, "read", f"cache.full/{project or 'all'}")
    try:
        cache = json.loads(CACHE_FILE.read_text())
    except Exception:
        return {"error": "cache not ready", "generated_at": None}
    return _filter_cache_for_project(cache, project)

@router.get("/agents")
def get_agents(user: str = Depends(get_current_user)):
    log_action(user, "read", "cache.agents")
    cache = get_cache(user=user)
    return cache.get("agents", [])

@router.get("/tasks")
def get_tasks(user: str = Depends(get_current_user)):
    log_action(user, "read", "cache.tasks")
    cache = get_cache(user=user)
    return cache.get("tasks", [])

@router.get("/kanban")
def get_kanban_all(
    project: str = Query(""),
    user: str = Depends(get_current_user)
):
    log_action(user, "read", f"cache.kanban/{project or 'all'}")
    cache = get_cache(user=user)
    kb = cache.get("kanban_by_project", {})
    if project:
        return {project: kb.get(project, [])}
    return kb

@router.get("/kanban/{project}")
def get_kanban_project(project: str, user: str = Depends(get_current_user)):
    log_action(user, "read", f"cache.kanban.project/{project}")
    cache = get_cache(user=user)
    return cache.get("kanban_by_project", {}).get(project, [])

@router.get("/decisions")
def get_decisions(
    project: str = Query(""),
    user: str = Depends(get_current_user)
):
    log_action(user, "read", f"cache.decisions/{project or 'all'}")
    cache = get_cache(user=user)
    all_decisions = cache.get("decisions", [])
    if project:
        return [d for d in all_decisions if _matches_project(d, project)]
    return all_decisions

@router.get("/memory")
def get_memory(
    project: str = Query(""),
    user: str = Depends(get_current_user)
):
    log_action(user, "read", f"cache.memory/{project or 'all'}")
    cache = get_cache(user=user)
    memory = cache.get("memory", {})
    if project:
        return {k: v for k, v in memory.items() if _matches_project(v, project)}
    return memory

@router.get("/metrics")
def get_metrics(user: str = Depends(get_current_user)):
    log_action(user, "read", "cache.metrics")
    cache = get_cache(user=user)
    return cache.get("metrics", {})
