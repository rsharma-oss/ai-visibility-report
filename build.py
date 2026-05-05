#!/usr/bin/env python3
"""
build.py — AI Visibility Report Generator
Pulls data from AI Peekaboo API, generates LLM-powered action recommendations,
and injects everything into template.html to produce a self-contained report.

Usage:
    python3 build.py [--config config.json]
"""

import json
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from urllib.parse import urlparse

import requests

# ─── LLM provider configs ─────────────────────────────────────────────────────

PROVIDER_CONFIGS = {
    "anthropic":  {
        "base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-sonnet-4-6",
        "extra_headers": {"anthropic-version": "2023-06-01"},
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
        "extra_headers": {},
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-2.0-flash",
        "extra_headers": {},
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-2.0-flash",
        "extra_headers": {},
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "extra_headers": {},
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "anthropic/claude-sonnet-4-6",
        "extra_headers": {},
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "default_model": "mistral-large-latest",
        "extra_headers": {},
    },
}


def call_llm(provider, api_key, model, system_prompt, user_prompt, base_url=None):
    """Call any OpenAI-compatible LLM provider and return the text response."""
    if provider == "claude-cli":
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        cmd = ["claude", "-p", "-"]
        if model:
            cmd += ["--model", model]
        result = subprocess.run(cmd, input=full_prompt, capture_output=True, text=True, check=True)
        return result.stdout.strip()

    # Try native anthropic SDK first for "anthropic" provider (avoids OpenAI compat layer issues)
    if provider == "anthropic":
        try:
            import anthropic as _anthropic
            _client = _anthropic.Anthropic(api_key=api_key)
            _model = model or "claude-sonnet-4-6"
            for attempt in range(3):
                try:
                    _resp = _client.messages.create(
                        model=_model,
                        max_tokens=4096,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}],
                    )
                    return _resp.content[0].text.strip()
                except Exception as e:
                    if "rate_limit" in str(e).lower() or "429" in str(e):
                        wait = 30 * (attempt + 1)
                        print(f"  Rate limit hit, waiting {wait}s before retry {attempt+1}/3...")
                        time.sleep(wait)
                    else:
                        raise
            raise RuntimeError("LLM call failed after 3 retries")
        except ImportError:
            pass  # fall through to openai compat

    try:
        from openai import OpenAI
    except ImportError:
        print("Error: 'openai' package not installed. Run: pip install openai")
        sys.exit(1)

    pconf = PROVIDER_CONFIGS.get(provider, {})
    resolved_url = base_url or pconf.get("base_url", "https://api.openai.com/v1")
    extra_headers = pconf.get("extra_headers", {})

    client = OpenAI(api_key=api_key, base_url=resolved_url, default_headers=extra_headers)
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if "rate_limit" in str(e).lower() or "429" in str(e):
                wait = 30 * (attempt + 1)
                print(f"  Rate limit hit, waiting {wait}s before retry {attempt+1}/3...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("LLM call failed after 3 retries")


# ─── Config ──────────────────────────────────────────────────────────────────

def load_config(path="config.json"):
    if not os.path.exists(path):
        print(f"Error: config file not found at {path}")
        sys.exit(1)
    with open(path) as f:
        cfg = json.load(f)

    # Backward compat: old anthropic_api_key field
    if "anthropic_api_key" in cfg and "llm_api_key" not in cfg:
        cfg["llm_api_key"] = cfg["anthropic_api_key"]
        cfg.setdefault("llm_provider", "anthropic")

    required = ["aipeekaboo_api_key", "brands"]
    if cfg.get("llm_provider", "anthropic") != "claude-cli":
        required.append("llm_api_key")
    for key in required:
        if key not in cfg:
            print(f"Error: missing required config key: {key}")
            sys.exit(1)
    cfg.setdefault("llm_api_key", "none")
    return cfg


# ─── API helpers ─────────────────────────────────────────────────────────────

BASE_URL = "https://www.aipeekaboo.com/api/v1"


def api_get(api_key, path, params=None, retries=5):
    """GET request with rate-limit retry (reads X-RateLimit-Reset header)."""
    headers = {"X-API-Key": api_key}
    url = BASE_URL + path
    for attempt in range(retries):
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code == 429:
            reset = resp.headers.get("X-RateLimit-Reset")
            if reset:
                wait = max(1, int(reset) - int(time.time()))
            else:
                wait = 60
            print(f"  Rate limited. Waiting {wait}s before retry...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Failed after {retries} retries: GET {path}")


def fetch_all_prompts(api_key, brand_id):
    """Fetch all prompts for a brand with pagination."""
    prompts = []
    page = 1
    while True:
        data = api_get(api_key, f"/brands/{brand_id}/prompts",
                       params={"limit": 200, "page": page})
        batch = data.get("prompts") or data.get("data") or []
        prompts.extend(batch)
        pagination = data.get("pagination", {})
        if not pagination.get("hasMore", False):
            break
        page += 1
    return prompts


def fetch_prompt_detail(api_key, brand_id, prompt_id):
    """Fetch full prompt detail including history with sources and entities."""
    time.sleep(3)  # 20 req/min = 3s between calls
    return api_get(api_key, f"/brands/{brand_id}/prompts/{prompt_id}",
                   params={"include_full_response": "true"})


# ─── Classification helpers ───────────────────────────────────────────────────

DOMAIN_CAT_MAP = {
    "reddit.com": "Social Platform",
    "quora.com": "Social Platform",
    "linkedin.com": "Social Platform",
    "youtube.com": "Video Platform",
    "vimeo.com": "Video Platform",
    "g2.com": "Review Site",
    "capterra.com": "Review Site",
    "trustpilot.com": "Review Site",
    "producthunt.com": "Review Site",
    "medium.com": "Publishing Platform",
    "substack.com": "Publishing Platform",
    "github.com": "Developer Platform",
    "apps.shopify.com": "eCommerce Platform",
    "shopify.com": "eCommerce Platform",
}


def classify_domain(domain):
    if domain in DOMAIN_CAT_MAP:
        return DOMAIN_CAT_MAP[domain]
    if "ai" in domain:
        return "AI/SaaS Blog"
    return "Industry Blog"


def classify_url(url, domain, title=""):
    title = (title or "").lower()
    path = urlparse(url).path.lower()
    url_lower = url.lower()

    # domain_type
    if any(d in domain for d in ["instagram.com", "tiktok.com", "twitter.com", "x.com", "facebook.com", "reddit.com", "quora.com", "forocoches.com"]):
        domain_type = "social_media"
    elif any(d in domain for d in ["youtube.com", "vimeo.com"]):
        domain_type = "video"
    elif any(seg in path for seg in ["/docs/", "/help/", "/support/"]):
        domain_type = "documentation"
    elif any(seg in path for seg in ["/pricing", "/plans"]):
        domain_type = "product_page"
    elif any(seg in path for seg in ["/product/", "/products/", "/tienda/", "/shop/", "/comprar/", "/collections/"]):
        domain_type = "product_page"
    elif path.count("/") <= 1 or (path.count("/") == 2 and path.endswith("/")):
        domain_type = "homepage"
    else:
        domain_type = "article_page"

    # content_type — Spanish + English patterns
    listicle_patterns = [
        r'las?\s+\d+\s+mejores?', r'los?\s+\d+\s+mejores?', r'top\s+\d+',
        r'\d+\s+best', r'best\s+\d+', r'\bbest\b.{0,30}\b(supplement|protein|brand|product)',
        r'\btop\b.{0,30}\b(supplement|protein|brand|product)',
        r'/top-', r'/best-', r'/mejores?-', r'ranking', r'comparativa',
        r'mejores?\s+(suplementos?|proteinas?|marcas?|productos?)',
    ]
    comparison_patterns = [r'\bvs\b', r'\bversus\b', r'comparison', r'comparar', r'diferencia\s+entre', r'cual\s+es\s+mejor', r'alternative']
    howto_patterns = [r'\bc[oó]mo\b', r'\bhow\s+to\b', r'\bgu[ií]a\b', r'\bguide\b', r'\btutorial\b', r'qu[eé]\s+es\b', r'cu[aá]ndo\b']

    combined = title + " " + url_lower
    if any(re.search(p, combined) for p in listicle_patterns):
        content_type = "listicle_roundup"
    elif any(re.search(p, combined) for p in comparison_patterns):
        content_type = "comparison"
    elif any(re.search(p, combined) for p in howto_patterns):
        content_type = "how_to_guide"
    elif domain_type == "social_media":
        content_type = "social_media" if any(d in domain for d in ["instagram.com", "tiktok.com", "twitter.com", "x.com", "facebook.com"]) else "forum_thread"
    elif domain_type == "video":
        content_type = "video"
    elif domain_type == "product_page":
        content_type = "product_page"
    elif domain_type == "homepage":
        content_type = "brand_homepage"
    else:
        content_type = "article"

    return domain_type, content_type


def extract_domain(url):
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return url


def comp_domain_from_name(name):
    known = {
        "google": "google.com",
        "microsoft": "microsoft.com",
        "salesforce": "salesforce.com",
        "hubspot": "hubspot.com",
        "shopify": "shopify.com",
        "klaviyo": "klaviyo.com",
        "zendesk": "zendesk.com",
        "intercom": "intercom.com",
        "mailchimp": "mailchimp.com",
        "gorgias": "gorgias.com",
        "tidio": "tidio.com",
        "dynamic yield": "dynamicyield.com",
        "yotpo": "yotpo.com",
        "okendo": "okendo.io",
        "attentive": "attentive.com",
        "postscript": "postscript.io",
        "recart": "recart.com",
        "privy": "privy.com",
    }
    lower = name.lower()
    for k, v in known.items():
        if k in lower:
            return v
    slug = re.sub(r"[^a-z0-9]", "", lower)
    return slug + ".com"


# ─── Data processing ─────────────────────────────────────────────────────────

def _brand_context(text, brand_name, window=600):
    """Extract a text window centred on the brand mention in the full response."""
    if not text:
        return ""
    idx = text.find(brand_name)
    if idx == -1:
        # Try case-insensitive
        lower = text.lower()
        idx = lower.find(brand_name.lower())
    if idx == -1:
        return text[:window]
    start = max(0, idx - window // 3)
    end = min(len(text), idx + 2 * window // 3)
    excerpt = text[start:end].strip()
    if start > 0:
        excerpt = "…" + excerpt
    if end < len(text):
        excerpt = excerpt + "…"
    return excerpt


def process_brand_data(api_key, brand_cfg):
    """Fetch and process all data for a single brand."""
    brand_id = brand_cfg["id"]
    brand_name = brand_cfg["name"]

    print(f"  Fetching prompts for {brand_name}...")
    prompts_raw = fetch_all_prompts(api_key, brand_id)
    print(f"  Processing {len(prompts_raw)} prompts...")

    prompts_out = []
    all_citations = []  # (url, title, model_key)
    all_entities = []   # (name, entity_type, model_key)
    sentiment_mentions = []
    total_runs_analyzed = 0          # count of individual AI model runs processed
    brand_model_mention_counts = defaultdict(int)  # model_key -> runs where brand mentioned

    for p in prompts_raw:
        prompt_id = p.get("id") or p.get("promptId")
        prompt_text = p.get("promptText") or p.get("text") or ""

        try:
            detail = fetch_prompt_detail(api_key, brand_id, prompt_id)
        except Exception as e:
            print(f"    Warning: could not fetch detail for prompt {prompt_id}: {e}")
            detail = p

        history = (detail.get("data") or {}).get("history") or detail.get("history") or []

        models_data = {}
        scores = []
        mentions_count = 0
        prompt_comp_all = defaultdict(int)
        prompt_comp_by_model = defaultdict(lambda: defaultdict(int))

        for entry in history:
            model_key = entry.get("aiModel") or entry.get("model", "unknown")
            mentioned = entry.get("mentioned", False)
            score = entry.get("score", 0) or 0
            total_runs_analyzed += 1
            if mentioned:
                brand_model_mention_counts[model_key] += 1
            rank = entry.get("rank")
            sentiment = entry.get("sentiment")
            if sentiment:
                sentiment = sentiment.lower()
                if sentiment not in ("positive", "negative", "neutral", "uncertain"):
                    sentiment = "neutral"

            response_text = (
                entry.get("fullResponse") or
                entry.get("responseSnippet") or
                entry.get("responseText") or ""
            )
            snippet = response_text[:300] if response_text else ""

            # Collect competitors mentioned in this same response entry
            entry_comps = []
            for ent in (entry.get("brandMentions") or entry.get("entities") or []):
                ent_type = (ent.get("type") or ent.get("entityType") or "").lower()
                if ent_type in ("competitor", "untracked"):
                    ent_name = ent.get("entityName") or ent.get("name", "")
                    if ent_name and ent_name.lower() != brand_name.lower():
                        entry_comps.append({
                            "name": ent_name,
                            "rank": ent.get("rank"),
                            "score": ent.get("score"),
                        })
            for ec in entry_comps:
                if ec.get("name"):
                    prompt_comp_all[ec["name"]] += 1
                    prompt_comp_by_model[model_key][ec["name"]] += 1

            models_data[model_key] = {
                "mentioned": mentioned,
                "score": score,
                "rank": rank,
                "sentiment": sentiment,
                "snippet": snippet,
                "competitors": entry_comps[:8],
            }

            if mentioned:
                mentions_count += 1
                scores.append(score)

                if sentiment:
                    full_resp = (
                        entry.get("fullResponse") or
                        entry.get("response") or
                        entry.get("responseText") or ""
                    )
                    sentiment_mentions.append({
                        "prompt": prompt_text,
                        "model": model_key,
                        "rank": rank,
                        "score": score,
                        "sentiment": sentiment,
                        "reason": next(
                            (b.get("mentionSummary", "") for b in (entry.get("brandMentions") or [])
                             if (b.get("entityName") or "").lower() == brand_name.lower()),
                            entry.get("mentionSummary", "") or entry.get("sentimentReason") or ""
                        )[:400],
                        "context": _brand_context(full_resp, brand_name, 600) or snippet[:400],
                        "competitors": [
                            e.get("entityName") or e.get("name", "")
                            for e in (entry.get("brandMentions") or entry.get("entities") or [])
                            if (e.get("type") or e.get("entityType") or "").lower() in ("competitor", "untracked")
                        ],
                    })

            sources = (
                entry.get("sources") or
                entry.get("citedSources") or []
            )
            _entry_comp_names = [c["name"] for c in entry_comps if c.get("name")]
            for src in sources:
                url = src.get("url", "")
                title = src.get("title") or urlparse(url).path or url
                if url:
                    all_citations.append((url, title, model_key, _entry_comp_names))

            for ent in (entry.get("brandMentions") or entry.get("entities") or []):
                ent_type = (ent.get("type") or ent.get("entityType") or "").lower()
                if ent_type in ("competitor", "untracked"):
                    all_entities.append((ent.get("entityName") or ent.get("name", ""), "competitor", model_key))

            # Also extract agency names from fullResponse text (catches untracked competitors)
            full_resp = entry.get("fullResponse") or ""
            if full_resp:
                existing_names = {
                    (ent.get("entityName") or ent.get("name", "")).lower()
                    for ent in (entry.get("brandMentions") or [])
                }
                # Patterns covering bold markdown, bullet lists, numbered lists, colon-inline
                _extract_patterns = [
                    r'\*\*([A-Z][A-Za-zÀ-ÿ &.\-]+?)(?:\s*[:·\|])',     # **Agency Name:**
                    r'^\s*[\*\-]\s+([A-Z][A-Za-zÀ-ÿ &.\-]{3,40})\s*(?:[:–\|]|\n)',  # * Agency Name:
                    r'^\s*\d+[\.\)]\s+([A-Z][A-Za-zÀ-ÿ &.\-]{3,40})\s*(?:[:–\|]|\n)',  # 1. Agency Name:
                    r'^([A-Z][A-Za-zÀ-ÿ &.\-]{3,40}):\s+[A-Za-zÀ-ÿ]',  # Agency Name: description
                ]
                _non_agency = {
                    "google", "youtube", "chatgpt", "gemini", "perplexity", "bing", "meta",
                    "facebook", "instagram", "tiktok", "twitter", "linkedin", "openai",
                    "anthropic", "claude", "gpt", "copilot", "wordpress", "shopify",
                    "woocommerce", "prestashop", "magento", "semrush", "ahrefs", "moz",
                    "hubspot", "salesforce", "mailchimp", "analytics", "search console",
                    "amazon", "sortlist", "clutch", "goodfirms",
                }
                seen_in_entry = set(existing_names)
                for pat in _extract_patterns:
                    for m in re.finditer(pat, full_resp, re.MULTILINE | re.IGNORECASE):
                        raw_name = m.group(1).strip().rstrip(".:,")
                        if len(raw_name) < 4 or len(raw_name) > 50:
                            continue
                        lower_name = raw_name.lower()
                        if any(skip in lower_name for skip in _non_agency):
                            continue
                        if lower_name in seen_in_entry:
                            continue
                        # Must look like a proper name (starts with capital, not all caps fragment)
                        if not raw_name[0].isupper():
                            continue
                        if raw_name.upper() == raw_name and len(raw_name) < 6:
                            continue
                        seen_in_entry.add(lower_name)
                        all_entities.append((raw_name, "competitor", model_key))

        avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
        best_score = max(scores) if scores else 0

        _pc = {"all": sorted([{"name": k, "count": v} for k, v in prompt_comp_all.items()], key=lambda x: -x["count"])[:6]}
        for _mk, _cnt in prompt_comp_by_model.items():
            _pc[_mk] = sorted([{"name": k, "count": v} for k, v in _cnt.items()], key=lambda x: -x["count"])[:6]

        prompts_out.append({
            "id": prompt_id,
            "text": prompt_text,
            "avgScore": avg_score,
            "bestScore": best_score,
            "mentions": mentions_count,
            "totalRuns": len(history),
            "models": models_data,
            "_comps": _pc,
        })

    # ── PROMPT_COMPS ─────────────────────────────────────────────────────────
    prompt_comps_out = {}
    for _p in prompts_out:
        _pid = _p["id"]
        prompt_comps_out[_pid] = _p.pop("_comps", {"all": []})

    # ── Citations aggregation ─────────────────────────────────────────────────
    url_data = {}
    for url, title, model_key, _ in all_citations:
        if url not in url_data:
            url_data[url] = {"title": title, "count": 0, "models": set(), "mc": defaultdict(int)}
        url_data[url]["count"] += 1
        url_data[url]["models"].add(model_key)
        url_data[url]["mc"][model_key] += 1

    domain_counts = defaultdict(int)
    domain_url_list = defaultdict(list)
    domain_type_counts = defaultdict(int)
    content_type_counts = defaultdict(int)

    dcat = {}
    for url, info in url_data.items():
        domain = extract_domain(url)
        domain_counts[domain] += info["count"]
        dcat[domain] = classify_domain(domain)
        dt, ct = classify_url(url, domain, info["title"])
        domain_type_counts[dt] += info["count"]
        content_type_counts[ct] += info["count"]
        domain_url_list[domain].append({
            "url": url,
            "title": info["title"],
            "count": info["count"],
            "models": sorted(info["models"]),
            "mc": dict(info["mc"]),
            "pageType": dt,
            "contentType": ct,
        })

    top_domains = sorted(domain_counts.items(), key=lambda x: -x[1])[:20]
    top_listicles = []
    for domain, urls in domain_url_list.items():
        for u in urls:
            if u["contentType"] == "listicle_roundup":
                top_listicles.append({"domain": domain, "url": u["url"], "title": u["title"], "count": u["count"]})
    top_listicles = sorted(top_listicles, key=lambda x: -x["count"])[:10]

    citations_out = {
        "total": sum(info["count"] for info in url_data.values()),
        "uniqueUrls": len(url_data),
        "uniqueDomains": len(domain_counts),
        "domainTypes": sorted(
            [{"type": k, "count": v} for k, v in domain_type_counts.items()],
            key=lambda x: -x["count"]
        ),
        "contentTypes": sorted(
            [{"type": k, "count": v} for k, v in content_type_counts.items()],
            key=lambda x: -x["count"]
        ),
        "topDomains": [{"domain": d, "count": c} for d, c in top_domains],
        "topListicles": top_listicles,
    }

    top_40_domains = [d for d, _ in sorted(domain_counts.items(), key=lambda x: -x[1])[:40]]
    durl_brand = {}
    for domain in top_40_domains:
        urls_sorted = sorted(domain_url_list[domain], key=lambda x: -x["count"])[:12]
        durl_brand[domain] = urls_sorted

    # ── Competitors aggregation ──────────────────────────────────────────────
    INGREDIENT_STOPWORDS = {
        "proteina", "proteína", "creatina", "cafeina", "cafeína", "vitamina",
        "omega", "colágeno", "colageno", "aminoácidos", "aminoacidos", "bcaa",
        "glutamina", "zinc", "magnesio", "hierro", "calcio", "fibra", "azúcar",
        "azucar", "sodio", "potasio", "fosforo", "fósforo", "carbohidrato",
        "protein", "creatine", "caffeine", "collagen", "vitamin", "fiber",
        "glucose", "fructose", "sucrose", "sodium", "calcium", "iron",
    }

    # Case-insensitive accumulation
    comp_data_lower = defaultdict(lambda: {
        "canonical": "", "mentions": 0, "models": set(), "model_counts": defaultdict(int)
    })
    for name, etype, model_key in all_entities:
        if not name:
            continue
        key = name.lower()
        info = comp_data_lower[key]
        # Keep the longest/most-capitalised form as canonical
        if len(name) > len(info["canonical"]):
            info["canonical"] = name
        info["mentions"] += 1
        info["models"].add(model_key)
        info["model_counts"][model_key] += 1

    competitors_out = []
    for key, info in comp_data_lower.items():
        # Filter: min 3 mentions, min 3 chars, not an ingredient, not a number
        if info["mentions"] < 3:
            continue
        if len(key) < 3:
            continue
        if key in INGREDIENT_STOPWORDS:
            continue
        if key.replace(".", "").replace(",", "").isdigit():
            continue
        avg_score = round(info["mentions"] / max(total_runs_analyzed, 1) * 100, 1)
        competitors_out.append({
            "name": info["canonical"],
            "mentions": info["mentions"],
            "modelMentions": dict(info["model_counts"]),
            "avgScore": avg_score,
            "topSentiment": "neutral",
            "models": sorted(info["models"]),
            "summaries": [],
        })
    competitors_out.sort(key=lambda x: -x["mentions"])
    competitors_out = competitors_out[:100]  # cap at 100

    # Prepend the tracked brand itself as position-0 reference row
    brand_total_mentions = sum(brand_model_mention_counts.values())
    brand_avg_score = round(brand_total_mentions / max(total_runs_analyzed, 1) * 100, 1)
    brand_entry = {
        "name": brand_name,
        "mentions": brand_total_mentions,
        "modelMentions": dict(brand_model_mention_counts),
        "avgScore": brand_avg_score,
        "topSentiment": "positive",
        "models": sorted(brand_model_mention_counts.keys()),
        "summaries": [],
        "isBrand": True,
    }
    competitors_out.insert(0, brand_entry)

    comp_domains = {c["name"]: comp_domain_from_name(c["name"]) for c in competitors_out}

    # ── Sentiment summary ────────────────────────────────────────────────────
    sent_counts = {"positive": 0, "neutral": 0, "negative": 0, "uncertain": 0}
    for m in sentiment_mentions:
        s = m.get("sentiment") or "neutral"
        sent_counts[s] = sent_counts.get(s, 0) + 1

    sentiment_out = {
        "total_mentions": len(sentiment_mentions),
        **sent_counts,
        "mentions": sentiment_mentions,
    }

    # ── Model citations ──────────────────────────────────────────────────────
    model_cit = defaultdict(lambda: {
        "total": 0,
        "domains": defaultdict(int),
        "domain_types": defaultdict(int),
        "content_types": defaultdict(int),
    })
    for url, title, model_key, _ in all_citations:
        domain = extract_domain(url)
        dt, ct = classify_url(url, domain, title)
        model_cit[model_key]["total"] += 1
        model_cit[model_key]["domains"][domain] += 1
        model_cit[model_key]["domain_types"][dt] += 1
        model_cit[model_key]["content_types"][ct] += 1

    model_citations_out = {}
    for mk, info in model_cit.items():
        top_doms = sorted(info["domains"].items(), key=lambda x: -x[1])[:10]
        model_citations_out[mk] = {
            "total": info["total"],
            "uniqueDomains": len(info["domains"]),
            "topDomains": [{"domain": d, "count": c} for d, c in top_doms],
            "domainTypes": sorted(
                [{"type": k, "count": v} for k, v in info["domain_types"].items()],
                key=lambda x: -x["count"]
            ),
            "contentTypes": sorted(
                [{"type": k, "count": v} for k, v in info["content_types"].items()],
                key=lambda x: -x["count"]
            ),
        }

    # ── COMP_CITS: competitor-citation co-occurrence mapping ─────────────────
    _comp_cit_raw = defaultdict(lambda: defaultdict(lambda: {"count": 0, "models": set(), "title": ""}))
    for _url, _title, _model_key, _comp_names in all_citations:
        for _cname in _comp_names:
            if _cname:
                _comp_cit_raw[_cname][_url]["count"] += 1
                _comp_cit_raw[_cname][_url]["models"].add(_model_key)
                if not _comp_cit_raw[_cname][_url]["title"]:
                    _comp_cit_raw[_cname][_url]["title"] = _title

    def _is_real_brand(name):
        if re.search(r'\d', name):
            return False
        for kw in ["impact whey", "evolate", "premium body"]:
            if kw in name.lower():
                return False
        return True

    _comp_cits_map = {}
    for _cname, _url_info in _comp_cit_raw.items():
        if not _is_real_brand(_cname):
            continue
        if _cname.lower() in INGREDIENT_STOPWORDS:
            continue
        _url_list = sorted(
            [
                {
                    "url": _url,
                    "title": _info["title"].replace("—", " - ").replace("–", "-"),
                    "domain": extract_domain(_url),
                    "count": _info["count"],
                    "models": sorted(_info["models"]),
                    "pageType": classify_url(_url, extract_domain(_url), _info["title"])[0],
                    "contentType": classify_url(_url, extract_domain(_url), _info["title"])[1],
                }
                for _url, _info in _url_info.items()
            ],
            key=lambda x: -x["count"],
        )[:20]
        if _url_list:
            _comp_cits_map[_cname] = _url_list

    comp_cits_out = dict(
        sorted(_comp_cits_map.items(), key=lambda x: -sum(u["count"] for u in x[1]))[:20]
    )

    return {
        "prompts": prompts_out,
        "citations": citations_out,
        "competitors": competitors_out,
        "sentiment": sentiment_out,
        "modelCitations": model_citations_out,
        "durl": durl_brand,
        "dcat": dcat,
        "comp_domains": comp_domains,
        "prompt_comps": prompt_comps_out,
        "comp_cits": comp_cits_out,
    }


# ─── Actions generation ───────────────────────────────────────────────────────

def build_actions_prompt(brand_name, brand_domain, data):
    prompts_list = data["prompts"]
    total_prompts = len(prompts_list)
    mentioned_prompts = sum(1 for p in prompts_list if p["mentions"] > 0)
    vis_pct = round(100 * mentioned_prompts / total_prompts) if total_prompts else 0

    cit = data["citations"]
    top_domains_str = ", ".join(
        f"{d['domain']} ({d['count']})"
        for d in cit["topDomains"][:10]
    )

    competitors = data["competitors"][:5]
    comp_str = ", ".join(
        f"{c['name']} ({c['mentions']} mentions)"
        for c in competitors
    )

    content_types = cit["contentTypes"][:5]
    total_ct = sum(x["count"] for x in cit["contentTypes"]) or 1
    ct_str = ", ".join(
        f"{x['type']} {round(100*x['count']/total_ct)}%"
        for x in content_types
    )

    model_breakdown_lines = []
    model_mentions = defaultdict(lambda: {"mentioned": 0, "total": 0})
    for p in prompts_list:
        for mk, md in p["models"].items():
            model_mentions[mk]["total"] += 1
            if md.get("mentioned"):
                model_mentions[mk]["mentioned"] += 1
    for mk, counts in model_mentions.items():
        pct = round(100 * counts["mentioned"] / counts["total"]) if counts["total"] else 0
        model_breakdown_lines.append(
            f"{mk}: {pct}% visibility, mentioned in {counts['mentioned']} prompts"
        )

    top_listicles = cit.get("topListicles", [])[:5]
    listicles_str = ", ".join(
        f"{l['domain']} ({l['count']} cites)"
        for l in top_listicles
    )

    return f"""Analyze this AI visibility data for {brand_name} and generate exactly 6 prioritized action recommendations as a JSON array.

Brand: {brand_name} ({brand_domain})
Prompt visibility: {vis_pct}% ({mentioned_prompts} of {total_prompts} prompts trigger a mention)
Total AI citations in this space: {cit['total']} across {cit['uniqueDomains']} unique domains
Top cited domains: {top_domains_str}
Top competitors by AI mentions: {comp_str}
Dominant content types: {ct_str}
Model breakdown: {'; '.join(model_breakdown_lines)}
Top listicle/roundup articles (highest-priority inclusion targets): {listicles_str}

Return a JSON array of exactly 6 objects. Each object must have these exact fields:
{{
  "priority": "high" or "medium",
  "effort": "High effort" or "Med effort",
  "cat": one of "Visibility", "Content", "Citation Strategy", "Competitive",
  "icon": one of exactly: "alert", "list", "play", "zap", "chat", "map", "search", "shield", "target" -- NO emojis, these are string keys only,
  "title": "one clear directive -- what the brand should do (max 90 chars)",
  "signals": ["2-3 specific data points from the data above that make this urgent"],
  "favDomains": ["2-4 specific domain names relevant to this action"],
  "why": "one paragraph explaining the business reason, using specific numbers from the data",
  "steps": ["step 1", "step 2", "step 3", "step 4"],
  "outcome": "what improvement to expect and realistic timeframe",
  "platDomains": ["3-5 domain names relevant to this action for favicon display"]
}}

Rules:
- No em dashes anywhere. Use commas, colons, or reword.
- Every domain name, citation count, and competitor name must come from the data above.
- Write for an SEO/AEO practitioner -- someone who knows what a listicle, schema markup, and Reddit citation are.
- Frame recommendations around topic/entity ownership and getting listed in cited sources -- never say "target this prompt" or "submit to AI models".
- At least 2 of the 6 actions must have a step starting with "this week" or "today".
- Outcome timeframes: listicle inclusion = 60-90 days for citations; YouTube = 2-4 weeks; schema markup = 45-90 days.
- Return only the JSON array, no other text."""


def generate_actions(cfg, brand_name, brand_domain, data):
    provider = cfg.get("llm_provider", "anthropic")
    api_key = cfg["llm_api_key"]
    pconf = PROVIDER_CONFIGS.get(provider, {})
    model = cfg.get("llm_model") or pconf.get("default_model") if provider != "claude-cli" else cfg.get("llm_model")
    base_url = cfg.get("llm_base_url")

    print(f"  Generating actions for {brand_name} (via {provider} / {model})...")

    system = (
        "You are an expert SEO and AEO (Answer Engine Optimization) strategist. "
        "You generate highly specific, data-driven action recommendations for marketing teams. "
        "Your output is always JSON. Never use em dashes (--). "
        "Write in plain language for an SEO/AEO practitioner."
    )

    raw = call_llm(provider, api_key, model, system, build_actions_prompt(brand_name, brand_domain, data), base_url)

    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"```$", "", raw).strip()

    return json.loads(raw)


# ─── Template injection ───────────────────────────────────────────────────────

def brand_toggle_html(brands):
    parts = []
    for i, b in enumerate(brands):
        cls = "bt-btn active" if i == 0 else "bt-btn"
        fav_url = f"https://www.google.com/s2/favicons?domain={b['domain']}&sz=32"
        onclick = f"setBrand('{b['key']}',this)"
        parts.append(
            f'<button class="{cls}" onclick="{onclick}">'
            f'<img src="{fav_url}" onerror="this.style.display=\'none\'">{b["name"]}'
            f"</button>"
        )
    return "".join(parts)


def js_obj_literal(py_obj):
    return json.dumps(py_obj, ensure_ascii=False)


def inject_template(template_path, output_path, brands, D, DURL, DCAT, comp_domains,
                    BRAND_CFG, ACTIONS, PROMPT_COMPS, COMP_CITS):
    with open(template_path, encoding="utf-8") as f:
        html = f.read()

    replacements = {
        "%%BRAND_TOGGLE%%": brand_toggle_html(brands),
        "%%DATA%%": js_obj_literal(D),
        "%%DOMAIN_URLS%%": js_obj_literal(DURL),
        "%%DOMAIN_CATEGORIES%%": js_obj_literal(DCAT),
        "%%COMP_DOMAINS%%": js_obj_literal(comp_domains),
        "%%BRAND_CFG%%": js_obj_literal(BRAND_CFG),
        "%%ACTIONS%%": js_obj_literal(ACTIONS),
        "%%DEFAULT_BRAND%%": brands[0]["key"],
        "%%PROMPT_COMPS%%": js_obj_literal(PROMPT_COMPS),
        "%%COMP_CITS%%": js_obj_literal(COMP_CITS),
    }

    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    config_path = "config.json"
    if len(sys.argv) > 2 and sys.argv[1] == "--config":
        config_path = sys.argv[2]

    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, config_path)
    template_path = os.path.join(script_dir, "template.html")

    cfg = load_config(config_path)
    api_key = cfg["aipeekaboo_api_key"]
    brands_cfg = cfg["brands"]
    output_file = cfg.get("output_file", "report.html")
    output_path = os.path.join(script_dir, output_file)

    if not os.path.exists(template_path):
        print(f"Error: template.html not found at {template_path}")
        sys.exit(1)

    D = {
        "prompts": {},
        "citations": {},
        "competitors": {},
        "sentiment": {},
        "modelCitations": {},
    }
    DURL = {}
    DCAT = {}
    comp_domains_all = {}
    BRAND_CFG = {}
    ACTIONS = {}
    PROMPT_COMPS = {}
    COMP_CITS = {}

    for b in brands_cfg:
        brand_name = b["name"]
        brand_key = b["key"]
        brand_domain = b["domain"]

        print(f"\nProcessing brand: {brand_name}")

        brand_data = process_brand_data(api_key, b)

        D["prompts"][brand_name] = brand_data["prompts"]
        D["citations"][brand_name] = brand_data["citations"]
        D["competitors"][brand_name] = brand_data["competitors"]
        D["sentiment"][brand_name] = brand_data["sentiment"]
        D["modelCitations"][brand_name] = brand_data["modelCitations"]

        DURL[brand_name] = brand_data["durl"]
        DCAT.update(brand_data["dcat"])
        comp_domains_all.update(brand_data["comp_domains"])

        BRAND_CFG[brand_key] = {
            "key": brand_name,
            "name": brand_name,
            "url": brand_domain,
        }

        ACTIONS[brand_key] = generate_actions(cfg, brand_name, brand_domain, brand_data)
        PROMPT_COMPS.update(brand_data["prompt_comps"])
        COMP_CITS[brand_name] = brand_data["comp_cits"]

    print(f"\nWriting report to {output_file}...")
    inject_template(
        template_path,
        output_path,
        brands_cfg,
        D,
        DURL,
        DCAT,
        comp_domains_all,
        BRAND_CFG,
        ACTIONS,
        PROMPT_COMPS,
        COMP_CITS,
    )
    print(f"Done! Open {output_file} in your browser.")


if __name__ == "__main__":
    main()
