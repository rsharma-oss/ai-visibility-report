# Build an AI visibility report from your AI Peekaboo data

## What this command does

Validates your config, runs the full build pipeline, and delivers a ready-to-open HTML report. If anything goes wrong, it diagnoses the issue and offers to fix it.

---

## Steps

### 1. Check that config.json exists

Read `config.json`. If the file does not exist, tell the user and offer to create it from the example:

```bash
cp config.example.json config.json
```

After copying, read the file and walk the user through each field they need to fill in:
- `aipeekaboo_api_key` — their AI Peekaboo API key (should start with `pk_`, not the placeholder `pk_YOUR_KEY_HERE`)
- `anthropic_api_key` — their Anthropic API key (should start with `sk-ant-`, not `sk-ant-YOUR_KEY_HERE`)
- `brands` — at least one brand object with a valid UUID as the `id` field
- `report_title` — the title to show in the report header
- `output_file` — the filename for the output (default is fine as `report.html`)

Do not proceed until the config looks valid.

### 2. Validate the config values

Read `config.json` and check for these common mistakes:

- `aipeekaboo_api_key` is still `"pk_YOUR_KEY_HERE"` -- ask the user to replace it
- `anthropic_api_key` is still `"sk-ant-YOUR_KEY_HERE"` -- ask the user to replace it
- `brands` array is empty -- ask the user to add at least one brand
- Any brand has `"id": "brand-uuid"` (the placeholder) -- ask the user to replace it with their real brand UUID

Tell the user where to find brand IDs if they do not know: they appear in the AI Peekaboo dashboard URL when viewing a brand, or they can list all brands via:

```bash
curl https://www.aipeekaboo.com/api/v1/brands \
  -H "X-API-Key: <their key>"
```

Do not proceed if any placeholder values remain.

### 3. Run the build

Once the config looks valid, run:

```bash
python3 build.py
```

Stream the output to the user so they can see progress. The build fetches data prompt-by-prompt and will take several minutes for larger brand configs. This is normal. The AI Peekaboo Grow plan allows 20 requests/minute and the script handles rate limiting automatically.

### 4. Handle success

If the build exits with code 0, tell the user:
- The output file path (read `output_file` from `config.json`, default `report.html`)
- How to open it: `open report.html` on macOS, or drag it into a browser window
- Offer to help deploy it to GitHub Pages (see below)

### 5. Handle errors

If the build fails, diagnose the error from the output and offer to fix it.

Common errors and their fixes:

**Rate limit (429)**
The script has retry logic, but if it fails after retries the user may need to wait a few minutes and re-run. No code changes needed.

**Invalid API key / 401**
The API key in `config.json` is wrong or expired. Ask the user to check their AI Peekaboo account settings and update the key.

**Brand not found / 404**
The brand UUID in `config.json` does not match any brand the API key has access to. Help the user find the correct UUID via `GET /brands` or from the dashboard URL.

**"unknown" model names in the output**
This means somewhere in the data processing, `entry['model']` is being used instead of `entry['aiModel']`. Open `build.py`, find the history entry parsing code, and correct the field name to `aiModel`.

**Missing `anthropic` module**
Run `pip install -r requirements.txt` and try again.

**Empty or missing template.html**
The `template.html` file is required. If it is missing, tell the user to re-clone the repository.

---

## GitHub Pages deployment (offer after a successful build)

If the user wants to deploy, run these commands (substituting their preferred repo name):

```bash
REPO_NAME="brand-ai-visibility"  # user can customize this
mkdir /tmp/$REPO_NAME
cp report.html /tmp/$REPO_NAME/index.html
cd /tmp/$REPO_NAME
git init && git checkout -b main
git add index.html && git commit -m "AI Visibility Report"
gh repo create $REPO_NAME --public --source=. --remote=origin --push
```

After pushing, enable GitHub Pages:
```bash
gh api repos/:owner/$REPO_NAME/pages --method POST \
  --field source='{"branch":"main","path":"/"}'
```

The live URL will be `https://<username>.github.io/<repo-name>/`. It is usually available within 60 seconds.
