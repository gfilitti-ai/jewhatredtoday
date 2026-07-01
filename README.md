# Jew-hatred Today

A Drudge-style news aggregator tracking antisemitism and anti-Jewish hate across the
diaspora. Runs on your Mac every 4 hours; you paste the result into Squarespace.

## What it does

1. **Gathers** recent candidate headlines from Google News RSS (targeted antisemitism
   queries) plus direct beat feeds (JTA, Algemeiner). No API key needed for this step.
2. **Curates** with Claude (Opus 4.8): keeps genuine antisemitic-incident stories
   (hate crimes, vandalism, threats/plots, arrests & prosecutions, campus harassment,
   Holocaust denial, watchdog data) anywhere **outside Israel**; drops Israel-domestic
   news and Gaza-war geopolitics. Incidents that *reference* Israel/Gaza are kept as long
   as the incident itself is outside Israel and targets Jews or Jewish institutions.
   Ranks by significance and picks one story for the 🚨 SIREN.
3. **Prioritizes Gerard Filitti** — a dedicated `"Gerard Filitti"` search flags every
   article he appears in (including ones that only *quote* him, where his name isn't in
   the headline — e.g. Paul Kessler case coverage). The curator keeps the on-beat ones,
   floats them to the top, and promotes the top one to the SIREN. Off-topic pieces that
   merely quote him (unrelated legal/political news) are filtered out.
4. **Writes four files** into `public/` — two layouts, each in two forms:
   - Flat single column: `index.html` (preview) + `embed.html` (paste into Squarespace).
   - US / Global split: `index_sections.html` (preview) + `embed_sections.html` (paste).

Claude returns *indices* into the fetched candidate list, never re-typed URLs, so every
link is a real fetched URL.

---

## One-time setup

```bash
cd /Users/filitti/Downloads/jew-hatred-today
./setup_local.sh                       # creates venv, installs deps
echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env    # your key from console.anthropic.com
./run.sh                               # test run -> writes public/index.html + embed.html
open public/index.html                 # preview it
```

(No key yet? `./run.sh` still works via a cruder keyword-only fallback.)

### Schedule it every 4 hours (launchd)

```bash
cp com.jewhatredtoday.update.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.jewhatredtoday.update.plist
```

It runs immediately, then every 4 hours while you're logged in (missed runs fire on wake).
Logs go to `run.log`. To stop: `launchctl unload ~/Library/LaunchAgents/com.jewhatredtoday.update.plist`.

---

## Posting an update to Squarespace (manual)

1. Copy the layout you want to the clipboard:
   - Flat single column:  `./copy.sh`
   - US / Global split:    `./copy.sh sections`
2. In Squarespace: edit the page → open the **Code Block** → select all, delete, paste,
   Save.

(First time only: add a Code Block to the page. Code Blocks require a Squarespace
**Business plan** or higher.)

---

## Tuning

- **Priority names:** `PRIORITY_NAMES` in `generate.py` (default `["gerard filitti",
  "filitti"]`). Set `PRIORITY_AS_SIREN = False` to keep priority stories at the top of the
  list without forcing them into the red siren slot.
- **Sources / topics:** `QUERIES` and `DIRECT_FEEDS`.
- **Editorial scope:** the `SYSTEM` prompt (in-scope / out-of-scope rules).
- **Recency window:** `RECENCY` (`when:3d` → `when:1d`, `when:7d`, …).
- **Refresh cadence:** `StartInterval` in the `.plist` (seconds; 14400 = 4 hours).
- **Look:** the `_content()` function — only `<font>`/`<table>`/`<hr>`, no CSS, no JS.

## Files

- `generate.py` — the pipeline.
- `run.sh` / `setup_local.sh` / `copy.sh` — local runner, setup, clipboard helper.
- `com.jewhatredtoday.update.plist` — the 4-hour launchd schedule.
- `.env` — your `ANTHROPIC_API_KEY` (git-ignored).
- `public/index.html`, `public/embed.html` — flat layout (preview + paste fragment).
- `public/index_sections.html`, `public/embed_sections.html` — US/Global layout.
- `.github/workflows/update.yml` — optional cloud alternative (GitHub Actions + Pages),
  not used by the local workflow above.

## Notes / limitations

- Links are Google News redirect URLs; they resolve to the publisher in a browser. Swap in
  more direct feeds under `DIRECT_FEEDS` for clean publisher links.
- If Claude declines a run or the API is down, the page still builds via the keyword-only
  fallback (cruder filtering).
- `index.html` carries a plain-HTML `<meta http-equiv="refresh">`; the pasted Squarespace
  fragment does not (a Code Block can't set page `<meta>`), so the Squarespace page updates
  only when you paste a new version.
