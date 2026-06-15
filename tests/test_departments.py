"""
Tests for CrewAI Departments.
"""
import pytest
from backend.core.departments import CrewAIDepartment

def test_department_kickoff():
    """Test that a department can kick off a task."""
    dept = CrewAIDepartment("engineering")
    result = dept.kickoff("Refactor agent_growth.py to add retry logic")
    assert isinstance(result, str)
    assert len(result) > 0
