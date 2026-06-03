"""
Workspace API — GitHub repo binding for isolated agent workdirs.
Mounted under /api/plugins/jarvis-dashboard/v1/dashboard/workspace
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth.dependencies import get_current_user
from workspace_manager import (
    list_workspaces, clone_workspace, remove_workspace,
    workspace_status
)

router = APIRouter(prefix="/workspace", tags=["workspace"])

class CloneRequest(BaseModel):
    repo_url: str
    name: str | None = None

class RemoveRequest(BaseModel):
    name: str

@router.get("/list")
def ws_list(user=Depends(get_current_user)):
    try:
        return {"workspaces": list_workspaces()}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/clone")
def ws_clone(req: CloneRequest, user=Depends(get_current_user)):
    try:
        return clone_workspace(req.repo_url, req.name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except FileExistsError as e:
        raise HTTPException(409, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))

@router.post("/remove")
def ws_remove(req: RemoveRequest, user=Depends(get_current_user)):
    try:
        return remove_workspace(req.name)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))

@router.get("/status/{name}")
def ws_status(name: str, user=Depends(get_current_user)):
    try:
        return workspace_status(name)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
