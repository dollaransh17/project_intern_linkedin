# Autonomous Lead Enrichment Agent

A Python pipeline for the SoftwareBrio AI Engineer Intern take-home assignment. It visits a company homepage with Playwright, discovers relevant same-site pages, reduces rendered content to source-labelled readable text, and uses Groq structured outputs to produce validated company intelligence.

## What it produces

For every input domain, `output.json` includes:

- a two-sentence company overview;
- target audience / ICP;
- public or generic emails and their source page;
- supported leadership/team names, titles, and LinkedIn URLs when present in crawled page evidence;
- a `0.0`–`1.0` confidence score;
- page-level failures and LLM token usage, so one failed site does not stop the batch.

The crawler uses a real headless Chromium browser. It waits for JavaScript-rendered content, removes `script`, `style`, `svg`, navigation, header, footer, forms, and sidebars from a cloned DOM, then passes only bounded visible text plus its source URLs to the LLM. It never sends raw HTML trees. If a browser runtime cannot launch, an HTTP visible-text fallback preserves batch-level resilience; the result records that fallback under `errors`.

## Setup

Requirements: Python 3.11+ and a Groq API key for structured extraction.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

Set `GROQ_API_KEY` in `.env`. `GROQ_MODEL` defaults to `openai/gpt-oss-20b`, which supports strict JSON Schema outputs. The extractor uses Groq's OpenAI-compatible endpoint, so the rest of the pipeline remains unchanged. Do not commit `.env`.

## Run the required targets

```bash
lead-enrich --domains-file sample_domains.json --output output.json
```

If the host environment does not permit a browser process to launch, use the documented resilience mode below; it fetches public HTML and uses the same cleanup and structured extraction path, but cannot render client-side-only content:

```bash
lead-enrich --domains-file sample_domains.json --output output.json --http-only
```

Or pass domains directly:

```bash
lead-enrich postman.com supabase.com vapi.ai --output output.json
```

The command always writes a result for every requested domain. Individual navigation timeouts, HTTP errors, bot-challenge warnings, missing text, and LLM errors are represented under that domain's `errors` array instead of crashing the whole run.

## Sample output

After running the required command, keep the generated `output.json` as the submission's sample output. Its contents intentionally vary as websites change and as the LLM uses the current page evidence. `sample_domains.json` is the exact three-domain assignment input.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `CRAWL_TIMEOUT_MS` | `20000` | Per-page navigation timeout. |
| `MAX_SUBPAGES` | `1` | Relevant discovered same-site pages after the homepage. |
| `MAX_PAGE_CHARS` | `2000` | Text evidence cap per page. |
| `MAX_CONTEXT_CHARS` | `6000` | Total LLM evidence cap per domain. |
| `GROQ_INPUT_USD_PER_MILLION_TOKENS` | unset | Optional current input-token price for cost estimates. |
| `GROQ_OUTPUT_USD_PER_MILLION_TOKENS` | unset | Optional current output-token price for cost estimates. |

No cost is guessed: `estimated_cost_usd` is `null` unless both current model prices are explicitly configured. Token counts are still logged.

## Tests

```bash
pytest -q
```

The tests cover prompt-context cleanup and input normalisation; they do not call external websites or the OpenAI API.

## Loom walkthrough outline (2–3 minutes)

1. Show the package split: `crawler.py`, `preprocess.py`, `extractor.py`, and `pipeline.py`.
2. Show `.env` with the key value hidden, then run the required command.
3. Open `output.json` and point out evidence-backed fields, confidence, token usage, and non-fatal errors.
4. Mention the explicit structured JSON Schema validation and bounded text preprocessing.

## Submission email requirement

The assignment requires the applicant to personally answer the mandatory operations question with `Yes` or `No`; an omitted answer or `No` is disqualifying according to the brief. This repository does not choose that answer for you. Confirm the answer is truthful before submitting.

The brief also requires the applicant to verify their own eligibility, submit a GitHub repository link and a 2–3 minute Loom recording, include their LinkedIn profile, and use the prescribed email subject with their own full name.
