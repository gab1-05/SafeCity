"""
AI service tests: token-aware keyword matching and provider hardening.

These live in apps/ai/tests.py; pytest.ini opts this file in explicitly
(python_files/testpaths), so `pytest -q` runs them with everything else.
"""

from unittest.mock import patch

from apps.ai.services import MockAIProvider, OpenAICompatibleProvider


def suggest(description: str, title: str = "Incident report") -> dict:
    return MockAIProvider().suggest_category(title, description)


class TestTokenAwareKeywords:
    def test_electric_wires_matches_electrical_hazard(self):
        assert suggest("Electric wires hanging over the street")["category_slug"] == (
            "electrical-hazard"
        )

    def test_single_word_keywords_still_match_exactly(self):
        assert suggest("A pothole has opened up near the junction")["category_slug"] == (
            "road-damage"
        )

    def test_plural_forms_still_match(self):
        assert suggest("Multiple potholes on this road")["category_slug"] == "road-damage"
        assert suggest("Streetlights are out again tonight")["category_slug"] == (
            "broken-streetlight"
        )
        assert suggest("Three cats blocking the lane")["category_slug"] == "stray-animal"

    def test_gerund_forms_still_match(self):
        assert suggest("Flooding near the subway entrance")["category_slug"] == "flooding"

    def test_substring_false_positives_are_not_matched(self):
        # "cat" must not fire on cattle/education, "fire" not on fireplace.
        assert suggest("Cattle at the education campus near the fireplace")[
            "category_slug"
        ] is None

    def test_word_boundary_false_positives_are_not_matched(self):
        # "wire" must not fire on "gwale"; "loud" not on "loudspeaker".
        assert suggest("The loudspeaker blares from the gwale hill")["category_slug"] is None

    def test_electricity_still_maps_to_electrical_hazard(self):
        assert suggest("Electricity junction box is sparking")["category_slug"] == (
            "electrical-hazard"
        )

    def test_phrase_keywords_still_match_as_substrings(self):
        assert suggest("Report: road damage near the junction")["category_slug"] == (
            "road-damage"
        )
        assert suggest("The street light flickers all night")["category_slug"] == (
            "broken-streetlight"
        )

    def test_confidence_formula_shape_is_unchanged(self):
        assert suggest("A pothole has opened up")["confidence"] == 0.5  # 0.35 + 1 * 0.15
        assert suggest("")["confidence"] == 0.2  # no hits


class TestMockSeverity:
    def test_critical_words_win(self):
        assert MockAIProvider().suggest_severity("Fire spreading fast")["severity"] == "critical"

    def test_high_words_win(self):
        assert MockAIProvider().suggest_severity("Waterlogging on the road")["severity"] == (
            "high"
        )

    def test_default_is_medium(self):
        assert MockAIProvider().suggest_severity("Paint peeling off a wall")["severity"] == (
            "medium"
        )


class TestOpenAISeverityValidation:
    def test_invalid_severity_falls_back_to_mock_heuristic(self):
        provider = OpenAICompatibleProvider()
        with patch.object(
            OpenAICompatibleProvider,
            "_chat",
            return_value={"severity": "catastrophic", "confidence": 0.9},
        ):
            result = provider.suggest_severity("The road is damaged")
        assert result["severity"] == "medium"  # mock fallback, not the hallucinated value

    def test_valid_severity_is_accepted(self):
        provider = OpenAICompatibleProvider()
        with patch.object(
            OpenAICompatibleProvider,
            "_chat",
            return_value={"severity": "Critical", "confidence": 0.7},
        ):
            result = provider.suggest_severity("Fire spreading")
        assert result == {"severity": "critical", "confidence": 0.7}
