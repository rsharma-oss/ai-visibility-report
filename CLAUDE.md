# CLAUDE.md — AI Visibility Report

## If a user just shared this repo URL and asked you to build a report

This is the most common entry point. The user has pasted the repo URL into Claude Code and asked you to create a report for their brand. Do the following in order — do not wait for the user to ask you for each step:

1. **Clone the repo** into a working directory:
   ```bash
   git clone https://github.com/filipelinsduarte/ai-visibility-report
   cd ai-visibility-report
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Collect the required config values.** If the user has already provided them in their message, use those directly. If not, ask for all of them at once in a single message — do not ask one by one:
   - AI Peekaboo API key (starts with `pk_`)
   - **LLM for action generation** — you have two paths:
     - **You are running inside Claude Code (most common):** use `llm_provider: "claude-cli"` and **no `llm_api_key` is needed**. The build script will call the `claude` CLI directly, which you already are. Do NOT ask the user for an Anthropic API key in this case.
     - **Running standalone / CI / another tool:** ask the user which LLM they have a key for. Common choices:
       - Anthropic / Claude: `sk-ant-...` → `llm_provider: "anthropic"`
       - OpenAI / ChatGPT: `sk-...` → `llm_provider: "openai"`
       - Google Gemini: `AIza...` → `llm_provider: "gemini"`
       - Groq: `gsk_...` → `llm_provider: "groq"`
       - OpenRouter: `sk-or-...` → `llm_provider: "openrouter"`
       - Mistral: `...` → `llm_provider: "mistral"`
       - Any OpenAI-compatible API: use `llm_provider: "openai"` and add `llm_base_url`
   - Optional: `llm_model` — defaults are set per provider, but they can override
   - Brand name, brand ID (UUID from the AI Peekaboo dashboard URL), and brand domain
   - Output filename (default: `report.html`)
   - If they want to compare two brands, collect details for both

4. **Create `config.json`** from the provided values. Use `config.example.json` as the structure reference. When running inside Claude Code, the config should look like:
   ```json
   {
     "aipeekaboo_api_key": "pk_...",
     "llm_provider": "claude-cli",
     "brands": [...]
   }
   ```
   No `llm_api_key` field is needed when `llm_provider` is `"claude-cli"`.

5. **Run the build:**
   ```bash
   python3 build.py
   ```
   This takes 5-6 minutes for a 30-prompt brand. Tell the user upfront so they are not surprised. Stream the output so they can see progress.

6. **Report back** with the output file path. Ask if they want to deploy to GitHub Pages or just use the file locally.

Do not ask the user to do any of these steps themselves. You have all the tools to handle them.

---

## What this project is

This tool generates AI visibility prospect reports for marketing agencies. Each report shows a brand's visibility across 5 AI models (Perplexity, ChatGPT, Gemini, Google AIO, Google AI Mode), with prompts data, sentiment analysis, competitor rankings, citation analysis, and auto-generated action recommendations.

The pipeline fetches live data from the AI Peekaboo API, processes it, calls any configured LLM (Anthropic, OpenAI, Gemini, Groq, Mistral, OpenRouter, or any OpenAI-compatible API) to generate 6 data-driven recommendations per brand, then injects everything into `template.html` and writes a single self-contained HTML file.

---

## Setup (follow these steps when a user first opens the project)

### 1. Check for config.json

If `config.json` does not exist, copy the example and prompt the user to fill it in:

```bash
cp config.example.json config.json
```

Then ask the user to provide:
- `aipeekaboo_api_key` — their AI Peekaboo API key (starts with `pk_`)
- `llm_provider` — which LLM to use: `"anthropic"`, `"openai"`, `"gemini"`, `"groq"`, `"openrouter"`, `"mistral"`, or any OpenAI-compatible provider
- `llm_api_key` — their API key for the chosen provider
- `llm_model` — (optional) override the default model for that provider
- `llm_base_url` — (optional) custom base URL for self-hosted or unlisted OpenAI-compatible APIs
- `brands` — an array of brand objects (see below)
- `report_title` — the title shown in the report header
- `output_file` — filename for the generated report (default: `report.html`)

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Finding brand IDs

Brand IDs are UUIDs. There are two ways to find them:

**From the dashboard URL**: When viewing a brand in the AI Peekaboo dashboard, the UUID appears in the URL, e.g. `https://app.aipeekaboo.com/brands/3fa85f64-5717-4562-b3fc-2c963f66afa6`.

**Via API**: Call `GET https://www.aipeekaboo.com/api/v1/brands` with the header `X-API-Key: pk_...` to list all brands the key has access to.

---

## How to run a report

```bash
python3 build.py
```

This will:
1. Read `config.json`
2. Fetch all prompts for each brand from the AI Peekaboo API
3. Fetch full prompt detail with citations for each prompt
4. Process the data into structured objects
5. Call Claude to generate 6 action recommendations per brand
6. Inject everything into `template.html`
7. Write the output HTML file (default: `report.html`)

Open the output file directly in a browser, or deploy it to GitHub Pages.

A report with 30 prompts takes roughly 5-6 minutes due to rate limiting on the AI Peekaboo Grow plan (20 requests/minute). The build script handles this automatically with sleeps and retries — no action needed.

---

## Understanding how actions are generated

Actions are generated by an LLM call (via whichever provider is configured). They are NOT templates or pre-written copy.

Claude analyzes the actual brand data for each brand:
- Visibility percentage across models
- Top cited domains and how often they appear
- Competitor landscape and their relative visibility
- Content type breakdown (articles, product pages, reviews, etc.)
- Sentiment distribution across prompts
- Prompts where the brand is absent or weak

Every domain name, citation count, and competitor mentioned in the actions comes from the real data fetched from AI Peekaboo. Two brands in the same industry will receive completely different recommendations.

**Style rules for generated actions:**
- Written for SEO/AEO practitioners in plain language
- No em dashes anywhere in generated content
- Framing is always about topic/entity ownership and getting listed in cited sources
- Never use the phrases "targeting prompts" or "submitting to AI models"
- Recommendations are specific and actionable, not generic advice

---

## When helping a user in this project

1. **Always read `config.json` first** to understand which brands are configured, what their IDs are, and what the output file is named.

2. **If the user asks to build a report**, run `python3 build.py`. You can use the `/build-report` slash command for a guided flow.

3. **Common errors and fixes:**

   | Error | Likely cause | Fix |
   |---|---|---|
   | `"unknown"` model names everywhere | Using `entry['model']` instead of `entry['aiModel']` | The field is `aiModel` in history entries — check `build.py` |
   | 429 rate limit errors | Too many API requests in a short window | The build script has built-in retry logic; if it persists, increase sleep intervals |
   | Missing API key errors | Placeholder values still in `config.json` | Ask the user to replace `pk_YOUR_KEY_HERE` and set `llm_provider` + `llm_api_key` |
   | Empty citation data | `include_full_response=true` not passed | Verify the prompt detail endpoint includes this query param |
   | Brand not found (404) | Wrong brand UUID in config | Re-check the brand ID from the dashboard URL or via `GET /brands` |

4. **If the user wants to customize the report**: Update `config.json` for title and metadata changes. Edit `template.html` for visual/layout changes. Avoid modifying `build.py` unless the user needs to change data processing logic.

5. **If the user wants to deploy**, help them push to GitHub Pages (see section below).

---

## Data quality rules

These apply every time you build or debug a report. They prevent the most common output quality issues.

### Competitor data
- `brandMentions[]` in history entries only contains entities that AI Peekaboo has tracked. The full AI response (`fullResponse`) always contains additional competitor agency names that are not in the tracked list.
- `build.py` already runs a fullResponse regex extraction pass in addition to brandMentions. If you are debugging low competitor counts, verify this pass is running and the `_extract_patterns` list covers markdown bold (`**Name:**`), bullet lists, numbered lists, and inline colon patterns.
- Filter out generic tools/platforms (Google, YouTube, ChatGPT, Semrush, Shopify, sortlist directories, etc.) from extracted names — these are not competitors.

### Sentiment context
- The `context` field in each sentiment mention must come from a window of `fullResponse` text centred on the brand mention, not from `responseSnippet` (which is capped at 200 chars).
- The `reason` field must come from `brandMentions[].mentionSummary` (where `entityName` matches the brand), falling back to the entry-level `mentionSummary`. The field `sentimentReason` does not exist in the API — using it always returns empty.

### Action cards
- The `icon` field must be one of exactly 9 string keys: `alert`, `list`, `play`, `zap`, `chat`, `map`, `search`, `shield`, `target`. Never emojis. The LLM prompt must be explicit: "these are string keys only, no emojis".
- The `effort` field must be exactly `"High effort"` or `"Med effort"` — not `"High priority"`.
- Every `signals` entry must reference a real number from the brand's actual data (citation counts, visibility percentages, competitor mention counts).
- Every `steps` entry that names a domain must use a domain that actually appears in the brand's citation data — not a generic example.

### Header HTML (when injecting into template)
- Brand toggle button: must use the brand's own domain for the Google favicon (`https://www.google.com/s2/favicons?domain={brand_domain}&sz=32`), not any template brand domain.
- Report date in `.h-meta`: must match the actual month/year the report was generated.

### API field names (AI Peekaboo history entries)
| Correct field | Wrong field (do not use) |
|---|---|
| `entry["aiModel"]` | `entry["model"]` (always undefined) |
| `entry["responseSnippet"]` | `entry["snippet"]` |
| `entry["mentionSummary"]` | `entry["sentimentReason"]` (does not exist) |
| `entry["fullResponse"]` | `entry["response"]` or `entry["responseText"]` |
| `brandMentions[i]["entityName"]` | `brandMentions[i]["name"]` |
| `brandMentions[i]["mentionSummary"]` | `brandMentions[i]["reason"]` |

---

## GitHub Pages deployment

To deploy the report as a public GitHub Pages site:

```bash
REPO_NAME="brand-ai-visibility"  # customize this
mkdir /tmp/$REPO_NAME
cp report.html /tmp/$REPO_NAME/index.html
cd /tmp/$REPO_NAME
git init && git checkout -b main
git add index.html && git commit -m "AI Visibility Report"
```

Then push to GitHub and enable Pages. Using the `gh` CLI:

```bash
gh repo create $REPO_NAME --public --source=/tmp/$REPO_NAME --remote=origin --push
# Then enable Pages via the repo settings, or:
gh api repos/:owner/$REPO_NAME/pages --method POST --field source='{"branch":"main","path":"/"}'
```

The deployed URL will be `https://<username>.github.io/<repo-name>/`.

---

## Important API field note

In AI Peekaboo API history entries, the model name field is `aiModel`, NOT `model`.

```python
# Correct
model_name = entry['aiModel']

# Wrong -- returns None or KeyError
model_name = entry['model']
```

If you see "unknown" as the model name everywhere in a report, this is the cause. The `build.py` script handles this correctly, but keep it in mind if you are debugging or extending the data processing code.

---

## Project file map

| File | Purpose |
|---|---|
| `build.py` | Main pipeline: fetch data, process, generate actions, write HTML |
| `template.html` | Dashboard template with `%%PLACEHOLDER%%` markers |
| `config.json` | User's local config (gitignored) |
| `config.example.json` | Example config committed to the repo |
| `requirements.txt` | Python dependencies |
| `CLAUDE.md` | This file |
| `README.md` | Public documentation |
| `.claude/commands/build-report.md` | `/build-report` slash command |
