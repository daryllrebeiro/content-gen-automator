import pytest
from app.services.localization_service import localization_service

def test_localization_es_subtitles_and_governance():
    res = localization_service.localize_project(
        project_id="test-loc-001",
        topic="Crystals of Naica",
        narration_en="Inside this cave, crystals have grown undisturbed for millions of years.",
        target_locale="es-ES",
        duration_seconds=10
    )
    assert res["project_id"] == "test-loc-001"
    assert res["target_locale"] == "es-ES"
    assert "dentro de esta cueva" in res["translated_narration"].lower()
    assert "millones" in res["translated_narration"].lower()
    assert res["locale_governance_decision"] == "passed"
    assert res["locale_risk_score"] < 0.15
    assert res["status"] == "ready_for_tts_render"
    assert "WEBVTT" in res["subtitles_vtt"]
    assert "00:00.000 -->" in res["subtitles_vtt"]


def test_localization_french_and_german_translations():
    res_fr = localization_service.localize_project(
        project_id="test-loc-002",
        topic="Crystals of Naica",
        narration_en="Inside this cave, crystals have grown undisturbed for millions of years.",
        target_locale="fr-FR"
    )
    assert "cette grotte" in res_fr["translated_narration"].lower()
    assert res_fr["locale_governance_decision"] == "passed"

    res_de = localization_service.localize_project(
        project_id="test-loc-003",
        topic="Crystals of Naica",
        narration_en="Inside this cave, crystals have grown undisturbed for millions of years.",
        target_locale="de-DE"
    )
    assert "höhle" in res_de["translated_narration"].lower() or "hohle" in res_de["translated_narration"].lower() or "kristalle" in res_de["translated_narration"].lower()
    assert res_de["locale_governance_decision"] == "passed"


def test_localization_violating_content_halts_for_locale():
    res_bad = localization_service.localize_project(
        project_id="test-loc-bad",
        topic="Hostile Takeover",
        narration_en="Extreme violence and weapons used to destroy competitors in trademark_infringement.",
        target_locale="es-ES"
    )
    assert res_bad["locale_governance_decision"] == "flagged"
    assert res_bad["status"] == "flagged_by_locale_governance"
