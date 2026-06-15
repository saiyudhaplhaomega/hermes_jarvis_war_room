"""
Tests for TuningEngine.
"""
import pytest
import os
import json
from backend.core.model_invoker import TuningEngine

def test_tuning_engine_log_feedback(tmp_path):
    """Test feedback logging for continuous learning."""
    feedback_path = tmp_path / "feedback.jsonl"
    engine = TuningEngine("test-project")
    engine.log_feedback("task-123", "success", "codex/gpt-5.5")
    with open(feedback_path, "r") as f:
        feedback = [json.loads(line) for line in f]
    assert len(feedback) == 1
    assert feedback[0]["outcome"] == "success"
