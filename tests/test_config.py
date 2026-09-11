from lead_enrichment.config import Settings


def test_settings_reads_groq_configuration(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")

    settings = Settings.from_environment()

    assert settings.groq_api_key == "test-key"
    assert settings.groq_model == "openai/gpt-oss-20b"
    assert settings.google_search_api_key is None
    assert settings.google_search_engine_id is None


def test_settings_requires_both_google_search_values(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "google-key")
    monkeypatch.delenv("GOOGLE_SEARCH_ENGINE_ID", raising=False)

    try:
        Settings.from_environment()
    except ValueError as error:
        assert "must both be set" in str(error)
    else:
        raise AssertionError("Expected incomplete Google search configuration to fail")
