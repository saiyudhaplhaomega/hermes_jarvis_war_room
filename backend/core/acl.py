"""
PolicyEngine for durable handoffs (zero-trust).

Usage:
    from backend.core.acl import PolicyEngine
    engine = PolicyEngine("my-project")
    if engine.authorize_handoff("engineering", "product", "task-123"):
        # Proceed with handoff
"""
from __future__ import annotations

import json
import os
from typing import Optional

class PolicyEngine:
    """Zero-trust handoff controls with audit trails."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.policies = self._load_policies()

    def _load_policies(self) -> dict:
        """Load policies from ~/.hermes/memory/projects/<project_id>/policies.json."""
        policy_path = os.path.expanduser(
            f"~/.hermes/memory/projects/{self.project_id}/policies.json"
        )
        try:
            with open(policy_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "engineering→product": {"allowed": True, "max_handoffs": 3},
                "product→marketing": {"allowed": True, "max_handoffs": 1},
                "marketing→finance": {"allowed": False, "reason": "Compliance"}
            }

    def authorize_handoff(self, from_dept: str, to_dept: str, task_id: str) -> bool:
        """Authorize a handoff between departments."""
        policy_key = f"{from_dept}→{to_dept}"
        policy = self.policies.get(policy_key)
        if not policy or not policy.get("allowed", False):
            return False
        # Check handoff count (e.g., via memory_router.py)
        return True

    def log_handoff(self, from_dept: str, to_dept: str, task_id: str, approved: bool) -> None:
        """Log handoff attempt for audit trail."""
        log_path = os.path.expanduser(
            f"~/.hermes/memory/projects/{self.project_id}/handoffs.log"
        )
        with open(log_path, "a") as f:
            f.write(json.dumps({
                "from": from_dept,
                "to": to_dept,
                "task_id": task_id,
                "approved": approved,
                "timestamp": int(time.time())
            }) + "\n")

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
import os

class ZeroTrustHandoff:
    """Cryptographically enforced handoffs between departments."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.keys = self._load_keys()

    def _load_keys(self) -> dict:
        """Load or generate RSA keys for each handoff policy."""
        keys = {}
        for policy in ["engineering→product", "product→marketing"]:
            if not os.path.exists(f"keys/{policy}_private.pem"):
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                    backend=default_backend()
                )
                public_key = private_key.public_key()
                self._save_key(private_key, f"keys/{policy}_private.pem")
                self._save_key(public_key, f"keys/{policy}_public.pem")
            else:
                private_key = self._load_key(f"keys/{policy}_private.pem")
                public_key = self._load_key(f"keys/{policy}_public.pem")
            keys[policy] = {"private_key": private_key, "public_key": public_key}
        return keys

    def _save_key(self, key, path: str):
        """Save key to file."""
        with open(path, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ) if isinstance(key, rsa.RSAPrivateKey) else key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))

    def _load_key(self, path: str):
        """Load key from file."""
        with open(path, "rb") as f:
            return serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            ) if "private" in path else serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )

    def sign_handoff(self, from_dept: str, to_dept: str, task_id: str) -> str:
        """Sign handoff with private key."""
        private_key = self.keys[f"{from_dept}→{to_dept}"]["private_key"]
        signature = private_key.sign(
            task_id.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return signature.hex()

    def verify_handoff(self, from_dept: str, to_dept: str, task_id: str, signature: str) -> bool:
        """Verify handoff with public key."""
        public_key = self.keys[f"{from_dept}→{to_dept}"]["public_key"]
        try:
            public_key.verify(
                bytes.fromhex(signature),
                task_id.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except:
            return False

import os

class DynamicACL:
    """Dynamic least-privilege permissions for agents."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.policies = self._load_policies()

    def _load_policies(self) -> dict:
        """Load permission policies from environment variables."""
        return {
            "agent_growth": {
                "permissions": ["read:agents", "write:agents"],
                "ttl": int(os.getenv("AGENT_GROWTH_TTL", "3600"))
            },
            "kanban": {
                "permissions": ["read:tasks", "write:tasks"],
                "ttl": int(os.getenv("KANBAN_TTL", "1800"))
            }
        }

    def grant(self, agent_id: str, permission: str) -> bool:
        """Grant permission if allowed."""
        if agent_id not in self.policies:
            return False
        if permission in self.policies[agent_id]["permissions"]:
            return True
        return False

    def revoke(self, agent_id: str, permission: str) -> bool:
        """Revoke permission."""
        if agent_id in self.policies and permission in self.policies[agent_id]["permissions"]:
            self.policies[agent_id]["permissions"].remove(permission)
            return True
        return False

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
import os

class AgentIdentityVerifier:
    """Cryptographic agent identity verification."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.identities = self._load_identities()

    def _load_identities(self) -> dict:
        """Load agent identities from environment variables."""
        identities = {}
        for agent_id in ["agent_growth", "kanban"]:
            if not os.path.exists(f"keys/{agent_id}_public.pem"):
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                    backend=default_backend()
                )
                public_key = private_key.public_key()
                self._save_key(private_key, f"keys/{agent_id}_private.pem")
                self._save_key(public_key, f"keys/{agent_id}_public.pem")
            else:
                public_key = self._load_key(f"keys/{agent_id}_public.pem")
            identities[agent_id] = {
                "public_key": public_key,
                "fingerprint": self._get_fingerprint(public_key)
            }
        return identities

    def _save_key(self, key, path: str):
        """Save key to file."""
        with open(path, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ) if isinstance(key, rsa.RSAPrivateKey) else key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))

    def _load_key(self, path: str):
        """Load key from file."""
        with open(path, "rb") as f:
            return serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )

    def _get_fingerprint(self, public_key) -> str:
        """Get SHA-256 fingerprint of public key."""
        return hashes.Hash(hashes.SHA256(), backend=default_backend()).update(
            public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        ).hexdigest()

    def verify(self, agent_id: str, signature: str) -> bool:
        """Verify agent identity."""
        public_key = self.identities[agent_id]["public_key"]
        try:
            public_key.verify(
                bytes.fromhex(signature),
                agent_id.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except:
            return False
