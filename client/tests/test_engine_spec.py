from sl_db_engine_spec.metadata import d3format_from_metadata


def test_d3format_prefers_explicit_d3() -> None:
    metadata = {
        "unit": {"kind": "currency", "code": "USD"},
        "format": {"preset": "number", "precision": 0},
        "extensions": {"superset": {"d3format": "$,.2f"}},
    }

    assert d3format_from_metadata(metadata) == "$,.2f"


def test_d3format_tolerates_legacy_format_d3() -> None:
    metadata = {
        "unit": {"kind": "currency", "code": "USD"},
        "format": {"preset": "number", "precision": 0, "d3": "$,.2f"},
    }

    assert d3format_from_metadata(metadata) == "$,.2f"


def test_d3format_maps_portable_presets() -> None:
    assert d3format_from_metadata({"format": {"preset": "smart_number"}}) == (
        "SMART_NUMBER"
    )
    assert d3format_from_metadata({"format": {"preset": "number", "precision": 1}}) == (
        ",.1f"
    )
    assert d3format_from_metadata(
        {"format": {"preset": "percentage", "precision": 0}},
    ) == ".0%"
    assert d3format_from_metadata(
        {
            "unit": {"kind": "currency", "code": "USD"},
            "format": {"preset": "currency", "precision": 2},
        },
    ) == "$,.2f"


def test_d3format_omits_unknown_or_invalid_format() -> None:
    assert d3format_from_metadata({}) is None
    assert d3format_from_metadata({"format": {"preset": "duration"}}) is None
    assert d3format_from_metadata({"format": {"preset": "number", "precision": -1}}) == (
        ",.2f"
    )
