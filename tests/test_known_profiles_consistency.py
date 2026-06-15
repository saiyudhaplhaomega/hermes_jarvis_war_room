from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def test_known_profiles_is_registry_team_map_keys():
    from jarvis_company_os.registry import KNOWN_PROFILES, TEAM_MAP

    assert KNOWN_PROFILES == frozenset(TEAM_MAP.keys())
