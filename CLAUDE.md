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

## Interactive filtering architecture

The report is a fully client-side dashboard. Two global state variables drive all sections:

```js
let activeModel = 'all';        // 'all' | 'google-aio' | 'google-ai-mode' | 'gemini-2.5-flash' | 'sonar' | 'gpt-4o-mini'
let currentTimeRange = 'all';   // 'all' | 'last-20' | 'last-14' | 'last-7' | 'last-run'
```

Every `render*()` function must respond to both. The pattern:
1. `_applyTimeRange()` re-aggregates `D.prompts / citations / competitors / sentiment / modelCitations[bk]` from `RAW_HISTORY`
2. Each `render*()` function applies `activeModel` inline, reading from the already-filtered `D`

### RAW_HISTORY

`build.py` injects `const RAW_HISTORY=%%RAW_HISTORY%%;` — per-brand, per-prompt, per-entry raw history. Structure:

```js
RAW_HISTORY = {
  "peekaboo": {           // keyed by brand KEY (lowercase), NOT brand name
    runDates: ["2026-04-10", ...],   // sorted asc
    prompts: [{
      id: "uuid",
      text: "prompt text",
      entries: [{
        date: "2026-04-10",
        model: "sonar",              // model key
        hit: true,                   // brand mentioned?
        sc: 85,                      // score 0-100
        rk: 2,                       // rank
        snt: "positive",             // sentiment
        rsn: "reason text",
        ctx: "surrounding context",
        srcs: [{u, t, pt, ct}],      // url, title, pageType, contentType
        comps: ["Peec AI", "Profound"]  // competitors in this response
      }]
    }]
  }
}
```

`_buildPromptComps(bk)` and `_buildCompCits(bk)` compute their results directly from `RAW_HISTORY`, applying date filtering in-place. Unlike Vitaldin (which had pre-computed `PROMPT_COMPS`/`COMP_CITS` injected from build.py), this report computes everything client-side.

### CRITICAL: brand key naming distinction

Two different casings coexist and must not be confused:

| Variable | Value | Used as key in |
|---|---|---|
| `currentBrand` | `"peekaboo"` (lowercase) | `RAW_HISTORY`, `_compCitsCache` |
| `BRAND_CFG[currentBrand].key` = `bk` | `"Peekaboo"` (capital P) | `D.prompts`, `D.competitors`, `D.citations`, `D.sentiment`, `D.modelCitations` |

Calling `_getCompCits(bk)` or `RAW_HISTORY[bk]` with the capitalized key always returns `undefined`. Always pass `currentBrand` (lowercase) to functions that read RAW_HISTORY.

---

## Competitor deduplication

Both build.py and template.html deduplicate competitors independently:

**build.py** (`normalize_comp_name(name)`): strips domain TLDs, " AI" suffix — runs at build time. `name_to_canonical` maps every variant to its canonical form. `all_entities` is remapped to canonical names before `comp_data` aggregation, so `competitors_out` entries are already merged with correct `modelMentions` counts.

**JS** (`_normComp(name)`, `_dedupeComps(arr)`): client-side dedup for display lists. Run on `D.competitors[bk]` whenever competitors are rendered (competitor tab, citations dropdown, prompts icons).

`_dedupeComps` groups by `_normComp` key, picks canonical name by highest `mentions` count, sums all mentions **and aggregates `modelMentions`** (summing per-model counts across merged entries). Always call `_dedupeComps()` before rendering any competitor list.

`_buildCompCits` uses a two-pass approach: first groups all citation entries by `_normComp(compName)`, picks canonical, then stores under BOTH `canonical` name AND `__norm__<key>` fallback. Lookup tries both:
```js
compCits[activeCitComp] || compCits['__norm__' + _normComp(activeCitComp)]
```

---

## Time range filter

Four options: **All time** / **Last 20 days** / **Last 14 days** / **Last 7 days** / **Last run**.

`setTimeRange(range)` updates `currentTimeRange` and calls `_applyTimeRange()`, which either resets from `D_ORIG` (for "all") or calls `_computeFilteredData(brandKey)` to re-aggregate from `RAW_HISTORY` entries within the date window.

**Important**: `_buildPromptComps(bk)` and `_buildCompCits(bk)` do their own date filtering internally using the same `pcInRange()` pattern. Their results must be invalidated when time range changes: `_promptComps={}` and `_compCitsCache={}` are reset inside `_applyTimeRange()`.

---

## Prompts table

Default sort: **Visibility DESC** (applied on every render). Sort column state: `let sortCol='visibility', sortDir='desc'`.

**Visibility sort metric** (must be consistent with the badge display):
```js
// For 'all' model: fraction of distinct models with mentioned=true
av = Object.values(p.models).filter(m => m && m.mentioned).length / Object.values(p.models).length;
// For specific model:
av = (p.models[activeModel] && p.models[activeModel].mentioned) ? 1 : 0;
```
Do NOT use `p.mentions / p.totalRuns` — that's a historical ratio and gives different ordering than the badge.

**Mentioned / Not mentioned filter:**
```js
// Mentioned: any model has mentioned=true
Object.values(p.models).some(m => m && m.mentioned)
// Not mentioned: no model has mentioned=true
!Object.values(p.models).some(m => m && m.mentioned)
```
Do NOT use `p.mentions > 0` — that uses historical run count, not current model state.

**Top Competitors column**: 3 favicon icons for the top competitors for that prompt/model combo, powered by `_promptComps[promptId][modelKey || 'all']`. Hover tooltip shows name + count. Updates with both time range filter and model filter.

---

## Sentiment tab

**Sentiment filter bar** (above stat tiles): All / Positive / Neutral / Negative / Uncertain. State: `let sentimentFilter='all'`. Filters the mention cards only — tiles always show full counts for the active model.

**Tile counts** are model-aware:
- If `activeModel === 'all'`: use pre-aggregated `s.positive`, `s.neutral`, etc.
- If model is active: count mentions in `s.mentions.filter(m => m.model === activeModel)` per sentiment type.

**Mention cards** are filtered by BOTH `activeModel` and `sentimentFilter`.

---

## Overview line chart (Visibility Over Time)

- **All lines solid** (`borderDash: []`) — no dashed lines for competitors
- **Custom external tooltip** (`tooltip: {enabled: false, external: fn}`): renders favicons + brand/competitor labels + % values. The built-in colored-square tooltip is disabled.
- **Competitors hidden by default** in last-run mode (`showLine: !isLastRun`)

---

## Stat cards — Best Score

The Best Score card subtitle is model-aware:
- When a model is active: subtitle says "Rank 1 by [Model Name]" or "highest ranking by [Model Name]"
- When all models active: scan all prompts/models to find which model achieved the highest score, use that model in the subtitle

Never hardcode "Rank 1 by Perplexity" — always derive the model dynamically from `bestScoreModel`.

---

## Data quality rules

These apply every time you build or debug a report. They prevent the most common output quality issues.

### Competitor data

Competitor extraction is a two-pass process — both passes contribute to `all_entities`, which is then deduplicated and aggregated into `competitors_out`.

**Pass 1 — API `brandMentions[]`** (always runs):
Reads `entry.get("brandMentions")` from each history entry and filters to `type == "competitor"` or `"untracked"`. These are companies AI Peekaboo has explicitly tracked. Fast and structured, but limited to what's in the monitored entity list.

**Pass 2 — LLM NLP on `fullResponse`** (runs when `llm_cfg` is provided, which is always the case when using `config.json`):
After the history loop completes, `extract_competitors_llm()` batches all collected `fullResponse` texts (8 per batch) and calls the configured LLM to extract real company names — including ones mentioned in plain prose, not just structured lists. The LLM is explicitly instructed to:
- Include names mentioned inline in prose, not just bullet lists or headers
- Use canonical short names (e.g. "Cognex" not "Cognex Corporation")
- Exclude AI/search platforms, SEO tools, and generic phrases

This replaces the old regex approach (which matched structural patterns like `**Name:**` or `1. Name:`) that produced large numbers of false positives (section headers, fragment phrases like "Tell me:" or "Best for:" counted as competitors). The LLM pass is semantically aware and only returns proper company names.

**Ordering constraint — aggregation must happen after deduplication:**
`comp_data` (which produces `competitors_out` and `modelMentions`) is built from `all_entities` **after** `normalize_comp_name` deduplication remaps all names to their canonical forms. This ensures that "Cognex" and "Cognex Corporation" both contribute to a single entry's `modelMentions`, so per-model counts sum correctly to the total. If you ever need to move code in `process_brand_data()`, preserve this order: dedup → aggregate.

**`modelMentions` requirement:**
Each competitor object in `competitors_out` must include a `modelMentions` key: a dict mapping model key → mention count for that model (e.g. `{"sonar": 18, "gpt-4o-mini": 15, ...}`). The `comp_data` accumulator tracks these via `model_counts: defaultdict(int)`, incremented on every entity append. The sum of all values in `modelMentions` must equal `mentions` (the total). If they don't match, deduplication ran before aggregation — check the ordering.

**`_dedupeComps` in the template must aggregate `modelMentions`:**
The JS `_dedupeComps()` function merges duplicate competitor entries client-side. It must aggregate `modelMentions` by summing per-model counts across merged entries — otherwise the per-model counts are lost after dedup. The current implementation does this correctly. If you rewrite `_dedupeComps`, always include:
```js
if(c.modelMentions){Object.keys(c.modelMentions).forEach(function(mk){
  g.modelMentions[mk]=(g.modelMentions[mk]||0)+c.modelMentions[mk];
});}
```

**Overview tab competitor bar must use `c.modelMentions[activeModel]`, not RAW_HISTORY counts:**
The Overview tab's competitor mentions bar must read per-model counts from `c.modelMentions[activeModel]` (from `D.competitors`), not from `RAW_HISTORY.comps`. `RAW_HISTORY.comps` is populated only from API `brandMentions[]` — it does not include LLM NLP-extracted competitors, so any competitor found via the LLM pass would show 0 in the Overview bar if RAW_HISTORY counts are used.

### Sentiment context
- The `context` field in each sentiment mention must come from a window of `fullResponse` text centred on the brand mention, not from `responseSnippet` (which is capped at 200 chars).
- The `reason` field must come from `brandMentions[].mentionSummary` (where `entityName` matches the brand), falling back to the entry-level `mentionSummary`. The field `sentimentReason` does not exist in the API — using it always returns empty.

### Action cards
- The `icon` field must be one of exactly 9 string keys: `alert`, `list`, `play`, `zap`, `chat`, `map`, `search`, `shield`, `target`. Never emojis. The LLM prompt must be explicit: "these are string keys only, no emojis".
- The `effort` field must be exactly `"High effort"` or `"Med effort"` — not `"High priority"`.
- Every `signals` entry must reference a real number from the brand's actual data (citation counts, visibility percentages, competitor mention counts).
- Every `steps` entry that names a domain must use a domain that actually appears in the brand's citation data — not a generic example.

### Overview tab: model filter wiring rule

`renderOverview()` in `template.html` must wire its per-model citation charts to `D.modelCitations[bk][activeModel]`, not to the global `D.citations[bk]` object. Specifically:

- **Top Cited Domains** — must use `((mc&&mc.topDomains)||cit.topDomains).slice(0,8)`
- **Content Type Distribution** — must use `((mc&&mc.contentTypes)||cit.contentTypes).slice(0,6)`
- **Page Type Distribution** — must use `((mc&&mc.domainTypes)||cit.domainTypes).slice(0,6)`

Where `mc` is resolved at the top of `renderOverview()` as:
```js
var mc = activeModel !== 'all' && D.modelCitations && D.modelCitations[bk] && D.modelCitations[bk][activeModel]
  ? D.modelCitations[bk][activeModel] : null;
```

The fallback to global `cit` is intentional — when `activeModel === 'all'` or the per-model data is absent, global totals are shown.

Each of these three card sub-labels must also show the active model name when a filter is active. Use the same pattern as the Competitor Mentions card:
```js
+(activeModel!=='all'?(MODEL_META[activeModel]||{label:activeModel}).label+' · ':'')+
```

`renderCitations()` already uses this pattern correctly. When editing `renderOverview()`, make sure all three citation chart sections follow the same wiring. If you add a new per-model data field (e.g. top listicles per model), apply the same `(mc&&mc.field)||cit.field` fallback pattern.

---

## Model filter completeness checklist

This section documents exactly what data source every render function uses when a model filter is active (`activeModel !== 'all'`). Use it to verify correctness after any template edit and to prevent regressions.

### `renderStats()` — 6 stat cards

| Stat card | Filtered data source | Notes |
|---|---|---|
| AI Visibility % | `p.models[activeModel].mentioned` per prompt | `mentioned / totalRuns * 100`; `totalRuns` counts 1 per prompt when filtered |
| Model Runs | 1 per prompt (not `p.totalRuns`) | Counts prompts that have data for `activeModel` |
| Best Score | `p.models[activeModel].score` | Max across all prompts |
| Total Citations | `D.modelCitations[bk][activeModel].total` via `mc_s` | Falls back to `c.total` when `activeModel==='all'` |
| Unique Domains sub-text | `mc_s.topDomains.length` via `citUniq` | Falls back to `c.uniqueDomains`; fixed 2026-05 (was always global) |
| Sentiment Score % | `s.mentions.filter(m => m.model===activeModel)` | `sentPos / sentTotal * 100` |
| Avg Position | `p.models[activeModel].rank` per prompt | Only ranks from the active model |

### `renderPrompts()` — prompts table

| Column | Filtered data source | Notes |
|---|---|---|
| Visibility badge | `p.models[activeModel].mentioned` | Shows 100%/0% when model-filtered |
| Avg Position | `p.models[activeModel].rank` | Shows single rank, not average |
| Sentiment | `p.models[activeModel].sentiment` + `.score` | Shows per-model sentiment chip |
| Score (in sentiment cell) | `p.models[activeModel].score` | Shown as sub-label next to chip |
| Model dots | All models rendered; active model outlined in `--v` | Outline added 2026-05 for visual emphasis |
| Sort: visibility | `p.models[activeModel].mentioned ? 1 : 0` | Binary sort when filtered |
| Sort: position | `p.models[activeModel].rank || 999` | Per-model rank |
| Sort: sentiment | `sentWeight(p.models[activeModel].sentiment)` | Per-model sentiment weight |

### `renderSentiment()` — sentiment tab

| Element | Filtered data source | Notes |
|---|---|---|
| Tiles (Positive/Neutral/Negative/Uncertain) | `tileCounts` computed from filtered `mentions` | Fixed 2026-05; was using global `s.positive` etc. |
| Mention cards list | `mentions` filtered by `m.model===activeModel` | Already correct before 2026-05 audit |
| Card count sub-label | `mentions.length` (filtered) | Reflects filtered count |

### `renderCompetitors()` — competitors tab

| Element | Filtered data source | Notes |
|---|---|---|
| Competitor list | `comps.filter(c => c.models.indexOf(activeModel) > -1)` | Removes competitors with no data for active model |
| Sort order (when filtered) | Re-sorted by `_dc(c)` = `c.modelMentions[activeModel]` desc | Without this re-sort, order stays as "all models" order |
| Bar width `pct` | `_dc(c)` = `c.modelMentions[activeModel]` | `_dc` is a local helper defined inside `renderCompetitors` |
| Mention count label | `_dc(c)` (per-model) | Not `c.mentions` |
| Bar scale `max` | `_dc(comps[0])` after per-model sort | Correct relative scaling per model |
| Insight panel — dominant text | `_dc(top3[0])` | Per-model count |
| Insight panel — sentiment list | `c.topSentiment`, `c.avgScore` (global) | Sentiment/avgScore not broken down per-model in data |

### `renderCitations()` — citations tab

| Element | Filtered data source | Notes |
|---|---|---|
| `c` object | `D.modelCitations[bk][activeModel]` when filtered | Falls back to `D.citations[bk]`; `uniqueDomains` patched to `topDomains.length` |
| Page Type bars | `c.domainTypes` (from model-filtered `c`) | Correct |
| Content Type bars | `c.contentTypes` (from model-filtered `c`) | Correct |
| Top 20 domains list | `c.topDomains` (from model-filtered `c`) | Correct |
| Domain URL expansion | `DURL[bk][domain].filter(u => u.models.indexOf(activeModel) > -1)` | Filters URLs by model |
| Citation count in URL row | `u.mc[activeModel]` via `displayCount` | Per-model citation count per URL |
| Top Listicles | Always global `D.citations[bk].topListicles` | Not broken down per-model in data structure |

### `renderOverview()` — overview tab

| Element | Filtered data source | Notes |
|---|---|---|
| Model Coverage bars | Always per-model (iterates all models) | Not affected by `activeModel` filter |
| Competitor Mentions bars | `c.modelMentions[activeModel]` from `D.competitors` | Read directly from the data object — NOT from RAW_HISTORY counts |
| Sentiment Breakdown donut | `sentCounts` from filtered `sMentions` | `s.mentions.filter(m => m.model===activeModel)` |
| Content Type donut | `mc.contentTypes` via `(mc&&mc.contentTypes)||cit.contentTypes` | `mc = D.modelCitations[bk][activeModel]` |
| Page Type donut | `mc.domainTypes` via `(mc&&mc.domainTypes)||cit.domainTypes` | Same `mc` pattern |
| Top Cited Domains bars | `mc.topDomains` via `(mc&&mc.topDomains)||cit.topDomains` | Same `mc` pattern |

### `renderActionsGrid()` — actions tab

Actions are static per brand (generated at build time by LLM). They do not respond to the model filter — this is intentional, as actions are strategic recommendations for the overall brand, not per-model.

---

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
