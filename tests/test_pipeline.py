from lead_enrichment.pipeline import _normalise_domain
from lead_enrichment.schemas import CompanyIntelligence


def test_normalise_domain_adds_https_and_strips_path() -> None:
    assert _normalise_domain("supabase.com/pricing?plan=pro") == "https://supabase.com/"


def test_normalise_domain_rejects_invalid_input() -> None:
    assert _normalise_domain("not a valid domain") is None


def test_llm_schema_requires_every_extraction_field() -> None:
    schema = CompanyIntelligence.model_json_schema()

    assert set(schema["required"]) == set(schema["properties"])
    assert schema["additionalProperties"] is False
