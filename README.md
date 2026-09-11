# Autonomous Lead Enrichment Agent

A Python pipeline for the SoftwareBrio AI Engineer Intern take-home assignment. It visits a company homepage with Playwright, discovers relevant same-site pages, reduces rendered content to source-labelled readable text, and uses Groq structured outputs to produce validated company intelligence.

## What it produces

For every input domain, `output.json` includes:

- a two-sentence company overview;
- target audience / ICP;
- public or generic emails and their source page;
- supported leadership/team names, titles, and LinkedIn URLs when present in crawled page evidence;
- optional Google search evidence for leadership LinkedIn URLs when configured;
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

## Optional Google LinkedIn enrichment

When both `GOOGLE_SEARCH_API_KEY` and `GOOGLE_SEARCH_ENGINE_ID` are set in `.env`, the pipeline searches Google for `site:linkedin.com/in` profiles for leadership names found on the company website. It only accepts matching LinkedIn profile URLs and records the selected result under `external_searches`; a search failure is recorded under `errors` without discarding the domain result.

```dotenv
GOOGLE_SEARCH_API_KEY=your-google-api-key
GOOGLE_SEARCH_ENGINE_ID=your-programmable-search-engine-id
```

The integration uses Google's Custom Search JSON API. Google currently requires an API key and Programmable Search Engine ID, and its documentation says the API is closed to new customers. If these credentials are unavailable, leave both variables blank and the core website-only workflow remains enabled.

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

## Loom demo frontend

The repository includes a local browser dashboard that presents the same pipeline and loads the latest `output.json` on startup. It has no additional frontend dependency:

```bash
source .venv/bin/activate
python demo_server.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Use **Run enrichment** to call the real pipeline, or show the existing output immediately after the page loads. Keep **HTTP-only mode** enabled for a predictable local demo. The **Download** button exports the current JSON result.

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
| `GOOGLE_SEARCH_API_KEY` | unset | Optional Google Custom Search API key. |
| `GOOGLE_SEARCH_ENGINE_ID` | unset | Optional Programmable Search Engine ID; must be set with the API key. |

No cost is guessed: `estimated_cost_usd` is `null` unless both current model prices are explicitly configured. Token counts are still logged.

## Tests

```bash
pytest -q
```

The tests cover prompt-context cleanup and input normalisation; they do not call external websites or the OpenAI API.

## Architecture and AWS extension points

Open `architecture.excalidraw` in Excalidraw for the current end-to-end flow. The current application is local/CLI-first:

`domains → browser crawler → visible-text preprocessing → Groq structured extraction → optional Google LinkedIn lookup → Pydantic validation → output.json`

The diagram also marks AWS services as optional additions; they are not part of the current implementation:

- **ECS Fargate:** run the existing Playwright CLI in a container, which is a better fit for browser dependencies than a small Lambda function.
- **EventBridge:** start a scheduled or on-demand Fargate task.
- **Secrets Manager:** store `GROQ_API_KEY` outside images, source control, and plain task configuration.
- **S3:** store versioned `output.json` artifacts with encryption and lifecycle policies.
- **CloudWatch Logs:** capture task and crawl errors for operations.
- **SQS dead-letter queue:** retain failed batch requests for retry when the workflow becomes asynchronous.

Recommended improvement order: containerize the current CLI, add Secrets Manager and S3, then add EventBridge scheduling and an SQS retry/DLQ workflow. These extensions require AWS account setup and IAM decisions, so this repository does not deploy them automatically.

## Loom walkthrough outline (2–3 minutes)

1. Show the package split: `crawler.py`, `preprocess.py`, `extractor.py`, and `pipeline.py`.
2. Show `.env` with the key value hidden, then run the required command.
3. Open `output.json` and point out evidence-backed fields, confidence, token usage, and non-fatal errors.
4. Mention the explicit structured JSON Schema validation and bounded text preprocessing.

## Submission email requirement

The assignment requires the applicant to personally answer the mandatory operations question with `Yes` or `No`; an omitted answer or `No` is disqualifying according to the brief. This repository does not choose that answer for you. Confirm the answer is truthful before submitting.

The brief also requires the applicant to verify their own eligibility, submit a GitHub repository link and a 2–3 minute Loom recording, include their LinkedIn profile, and use the prescribed email subject with their own full name.
