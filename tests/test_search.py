import json

from lead_enrichment.search import GoogleSearchClient


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return self.payload


def test_google_search_returns_matching_linkedin_profile(monkeypatch) -> None:
    monkeypatch.setattr(
        "lead_enrichment.search.urlopen",
        lambda request, timeout: _Response(
            {
                "items": [
                    {
                        "title": "Abhinav Asthana - Co-Founder at Postman | LinkedIn",
                        "link": "https://www.linkedin.com/in/abhinav-asthana/",
                        "snippet": "Co-Founder at Postman",
                    }
                ]
            }
        ),
    )

    profile_url, evidence = GoogleSearchClient("key", "engine", 1_000).find_linkedin_profile(
        "Abhinav Asthana", "postman"
    )

    assert profile_url == "https://www.linkedin.com/in/abhinav-asthana/"
    assert len(evidence) == 1
    assert evidence[0].provider == "google_custom_search"
