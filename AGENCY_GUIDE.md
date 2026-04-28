# Agency Guide: Creating an AI Visibility Report

This guide walks you through creating an AI visibility prospect report using Claude Code. The report shows a brand's visibility across 5 AI models, including citation data, competitor analysis, and a personalised set of action recommendations generated from the data.

The whole process takes about 10 minutes of your time. The build itself runs on its own for 5-6 minutes while it fetches data.

---

## What you need before starting

**1. An AI Peekaboo account (Grow plan or above)**
You need an API key. Go to your AI Peekaboo dashboard, then Settings > Integrations > Generate API Key. Copy the key — it starts with `pk_`.

**2. The brand ID for the prospect you want to report on**
The brand must already be set up in your AI Peekaboo account with prompts tracked. To find the brand ID, open the brand in your dashboard and copy the UUID from the URL:
```
https://app.aipeekaboo.com/brands/3fa85f64-5717-4562-b3fc-2c963f66afa6
                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                   this is the brand ID
```
Or call `GET https://www.aipeekaboo.com/api/v1/brands` with your API key to list all brands.

**3. An Anthropic API key**
This is used to generate the action recommendations. Get one at console.anthropic.com. The key starts with `sk-ant-`.

**4. Claude Code installed**
Download from claude.ai/code if you don't have it yet.

---

## How to create the report

Open Claude Code and paste this message — fill in your own details:

```
I want to create an AI visibility prospect report.

Please use this repo: https://github.com/filipelinsduarte/ai-visibility-report

Here's my information:
- AI Peekaboo API key: pk_...
- Anthropic API key: sk-ant-...
- Brand name: Klaviyo
- Brand ID: 3fa85f64-5717-4562-b3fc-2c963f66afa6
- Brand domain: klaviyo.com
- Output file: klaviyo-visibility-report.html

Clone the repo, set up the config, and build the report.
```

That's it. Claude Code will:
1. Clone the repo to your machine
2. Create the config file with your details
3. Install the required Python packages
4. Fetch all the brand's data from AI Peekaboo (this takes 5-6 minutes — it's pulling data for every tracked prompt)
5. Generate personalised action recommendations from the data
6. Write a single HTML file you can open in any browser

---

## Running a report for two brands

If you want to compare two brands side by side (useful when prospecting within the same industry), include both in your message:

```
I want to create an AI visibility report comparing two brands.

Repo: https://github.com/filipelinsduarte/ai-visibility-report

AI Peekaboo API key: pk_...
Anthropic API key: sk-ant-...

Brand 1:
- Name: Klaviyo
- ID: 3fa85f64-5717-4562-b3fc-2c963f66afa6
- Domain: klaviyo.com
- Key: klaviyo

Brand 2:
- Name: Gorgias
- ID: 8d3c2a19-1234-5678-abcd-ef0123456789
- Domain: gorgias.com
- Key: gorgias

Output file: klaviyo-gorgias-report.html

Clone the repo, set up the config, and build the report.
```

The report will have a toggle at the top letting you switch between brands.

---

## Sharing the report

Once the HTML file is built, you have two options:

**Send the file directly** — attach the `.html` file to an email. The recipient opens it in their browser with no login or setup required.

**Publish to a URL** — deploy to GitHub Pages so you can share a link. Ask Claude Code:
```
Deploy this report to GitHub Pages so I can share a link.
```
Claude Code will handle the GitHub setup and give you a URL like `https://yourusername.github.io/klaviyo-visibility-report/`.

---

## What's in the report

The report has 6 sections accessible from the tabs at the top:

- **Overview** — charts showing model coverage, competitor mentions, sentiment breakdown, and citation source types
- **Prompts** — every tracked prompt with visibility percentage, average AI ranking position, and sentiment
- **Sentiment** — the exact AI responses where the brand was mentioned, with context
- **Competitors** — which competing brands appear most often in AI responses and with what sentiment
- **Citations** — the domains and articles that AI models are pulling from when answering questions in this space
- **Actions** — 6 prioritised recommendations generated from the data, specific to this brand

There is also a filter bar at the top to slice all sections by individual AI model (Perplexity, ChatGPT, Gemini, Google AIO, Google AI Mode).

---

## Common questions

**How long does the build take?**
About 5-6 minutes for a brand with 20-30 tracked prompts. The script fetches full response data for every prompt, which is rate-limited by the AI Peekaboo API.

**Does the brand need to be set up in AI Peekaboo already?**
Yes. The brand must have prompts tracked and at least one completed analysis run. The report builds from historical data — it does not run new AI queries.

**Can I run this again later with fresh data?**
Yes. Just ask Claude Code to rebuild the report whenever you want updated data pulled from AI Peekaboo.

**The actions look generic — is something wrong?**
The actions are generated by Claude based on the data. If they seem generic, the brand likely has very low visibility (0% across most prompts) and limited citation data to work with. That is itself a useful finding to show the prospect.

**I got a rate limit error**
The build script handles rate limiting automatically. If you see a persistent error, wait a few minutes and try again.
