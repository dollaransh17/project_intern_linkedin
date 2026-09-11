from lead_enrichment.config import Settings


def test_settings_reads_groq_configuration(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")

    settings = Settings.from_environment()

    assert settings.groq_api_key == "test-key"
    assert settings.groq_model == "openai/gpt-oss-20b"
