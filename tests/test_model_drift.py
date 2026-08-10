import pytest
from das_llm.drift import ModelDriftTracker


def test_model_drift_tracker_matching():
    tracker = ModelDriftTracker(expected_fingerprint="fp_gpt4o_2026")
    fp, drift = tracker.record_response({"system_fingerprint": "fp_gpt4o_2026"})
    assert fp == "fp_gpt4o_2026"
    assert drift is False


def test_model_drift_tracker_alert_on_change():
    tracker = ModelDriftTracker(expected_fingerprint="fp_gpt4o_2026_old")
    fp, drift = tracker.record_response({"system_fingerprint": "fp_gpt4o_2026_new"})
    assert fp == "fp_gpt4o_2026_new"
    assert drift is True
