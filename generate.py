#!/usr/bin/env python3
"""
Jew-hatred Today — a Drudge-style aggregator of antisemitic-incident news.

Pipeline:
  1. Gather candidate headlines from Google News RSS (topical queries) + direct feeds.
  2. Deduplicate.
  3. Curate with Claude (Opus 4.8): apply the editorial scope, drop Israel/Gaza
     geopolitics, rank by significance, pick ONE story for SIREN treatment.
  4. Render a single-column, <font>-tagged, no-CSS/no-JS HTML page.

No API key present? Falls back to a keyword-only ranker so the page still builds.
"""

import calendar
import html
import json
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

import feedparser

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "public/index.html")
MODEL = "claude-opus-4-8"
RECENCY = "when:3d"          # Google News recency operator (soft — leaks older items)
MAX_CANDIDATES = 150         # cap sent to the model, to bound token cost

# Hard age ceiling enforced in code (Google's when: filter is unreliable, and the
# direct feeds have none). Anything older than this is dropped outright.
MAX_AGE_DAYS = 7
PRIORITY_MAX_AGE_DAYS = 14   # priority (Filitti) coverage may be a little older
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Names to always surface and float to the very top, regardless of the rest of the
# beat. Matched as a case-insensitive substring on the headline.
PRIORITY_NAMES = ["gerard filitti", "filitti"]
PRIORITY_AS_SIREN = True     # promote the top priority story into the SIREN slot

# Dedicated searches for priority coverage. A Google News search for an exact name
# also returns articles that merely QUOTE the person (name not in the headline), so
# every result of these queries is flagged as priority — this catches pieces like the
# Cleveland Jewish News / JNS Paul Kessler stories where Filitti is a quoted source.
# Wider window than the main beat so his coverage is not missed.
PRIORITY_QUERIES = ["Gerard Filitti"]
PRIORITY_RECENCY = "when:14d"

# Topical Google News searches. Broad on purpose — Claude does the fine filtering.
QUERIES = [
    "antisemitic incident",
    "antisemitic attack",
    "antisemitic vandalism",
    "antisemitic graffiti",
    "antisemitic assault",
    "antisemitic harassment",
    "synagogue vandalized",
    "synagogue attack",
    "Jewish cemetery vandalized",
    "swastika vandalism",
    "hate crime Jewish",
    "attack on Jewish man OR woman OR student",
    "Jewish students harassed campus",
    "antisemitism arrest OR charged OR sentenced",
    "plot against synagogue OR Jewish",
    "Holocaust denial OR distortion",
    "antisemitic threats",
    "ADL antisemitic incidents",
    "antisemitism Europe",
    "antisemitism UK OR France OR Germany OR Australia OR Canada",
]

# A few direct beat feeds (aggregate a lot of diaspora-incident coverage).
DIRECT_FEEDS = [
    "https://www.jta.org/feed",
    "https://www.algemeiner.com/feed/",
]

SYSTEM = """\
You are the editor of "Jew-hatred Today", a no-frills news aggregator that tracks \
antisemitism and anti-Jewish hate in the diaspora. You are given a numbered list of \
recent candidate headlines. Select the ones that fit the beat, rank them, and pick \
ONE for siren treatment.

TOP PRIORITY - GERARD FILITTI:
- Some candidates are tagged [FILITTI] because a search for "Gerard Filitti" returned \
them; he may be a quoted source even when his name is not in the headline (for example, \
Paul Kessler case coverage). If a [FILITTI] story is on this publication's beat - \
antisemitism, anti-Jewish hate, a Jewish-community matter, or the Paul Kessler case - \
you MUST include it (the SINGLE best version of that event, not every outlet's copy), \
rank it at the very top, and prefer the most significant such story for the siren. IGNORE [FILITTI] items that are clearly off-topic (unrelated legal \
or political news that merely quotes him).

IN SCOPE (include):
- Antisemitic hate crimes, assaults, and violence against Jews or Jewish institutions.
- Vandalism/desecration: synagogues, Jewish cemeteries, schools, homes, businesses; \
swastikas and antisemitic graffiti.
- Threats, plots, and terrorism arrests/prosecutions targeting Jews or Jewish sites.
- Harassment and intimidation of Jews, including on campuses and at workplaces.
- Antisemitic rhetoric, incitement, or Holocaust denial/distortion by public figures, \
officials, clergy, or institutions.
- Prosecutions, sentencings, and law-enforcement actions in antisemitism cases.
- Watchdog data/reports on antisemitic incidents (e.g., ADL, CST).
- These may occur ANYWHERE OUTSIDE ISRAEL — the United States and the wider global \
diaspora (Europe, UK, Canada, Australia, Latin America, etc.).

An incident is IN SCOPE even when it references Israel or the Gaza war — e.g., a \
synagogue firebombed by an attacker citing Gaza, or a Jewish student threatened at a \
protest — SO LONG AS the incident itself occurs OUTSIDE ISRAEL and targets Jews or \
Jewish institutions/people.

OUT OF SCOPE (exclude):
- Anything happening INSIDE Israel (attacks in Israel, Israeli domestic news).
- Israeli military, government, or diplomatic developments; Gaza war coverage; \
hostage/ceasefire negotiations; Middle East geopolitics generally.
- Opinion, analysis, and think-pieces with no specific incident.
- Coverage that is about Israel/Palestine policy rather than about hatred of Jews.
- Duplicates and off-topic items. Do NOT pad the list to hit a number.

DEDUPLICATE BY EVENT (important):
- Many outlets cover the SAME incident with different headlines. Collapse all articles \
about one underlying event into a SINGLE best entry (clearest headline, most \
authoritative source) and drop the rest. The Paul Kessler sentencing, for example, must \
appear at most ONCE on the whole page. This applies to [FILITTI]-tagged items too: pick \
the single best version of an event, never several.

Rank the selected stories most-significant-first (severity, breaking-ness, scale, \
prominence). Choose the single most significant/severe/urgent story as the siren, and \
write a punchy, factual headline for it (it will be shown in ALL CAPS). Return indices \
that refer to the provided candidate list.

For EVERY selected story (and the siren), assign a region:
- "US"     — the incident occurred in the United States.
- "Global" — the incident occurred anywhere else in the diaspora (still outside Israel).
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "siren_index": {
            "type": "integer",
            "description": "Index of the single most significant story (siren).",
        },
        "siren_headline": {
            "type": "string",
            "description": "Punchy, factual headline for the siren story (shown ALL CAPS).",
        },
        "siren_region": {
            "type": "string",
            "enum": ["US", "Global"],
            "description": "Region of the siren story.",
        },
        "stories": {
            "type": "array",
            "description": "Remaining in-scope stories, ranked most significant first. Excludes the siren.",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer", "description": "Index into the candidate list."},
                    "region": {"type": "string", "enum": ["US", "Global"]},
                },
                "required": ["index", "region"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["siren_index", "siren_headline", "siren_region", "stories"],
    "additionalProperties": False,
}

# Keywords for the no-API fallback ranker.
INCLUDE_KW = [
    "antisemit", "anti-semit", "jew", "jewish", "synagogue", "swastika", "holocaust",
    "kosher", "rabbi", "yeshiva", "menorah", "hasidic", "orthodox jew",
]
EXCLUDE_KW = [
    "israel", "israeli", "gaza", "idf", "netanyahu", "hamas", "hostage", "ceasefire",
    "west bank", "tel aviv", "jerusalem", "knesset",
]


# ---------------------------------------------------------------------------
# Gather
# ---------------------------------------------------------------------------

def _fetch(url):
    return feedparser.parse(url, agent=UA)


def _clean_title(raw):
    """Google News titles look like 'Headline - Publisher'. Split off the source."""
    raw = html.unescape(raw or "").strip()
    source = ""
    if " - " in raw:
        head, tail = raw.rsplit(" - ", 1)
        # Treat the tail as the source only if it looks like a publisher name.
        if 0 < len(tail) <= 40 and "http" not in tail:
            raw, source = head.strip(), tail.strip()
    return raw, source


def _norm(title):
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


# Coarse US-vs-Global guess for the fallback path and for priority items the model
# didn't tag. The LLM path assigns regions directly; this is only a backstop.
_GLOBAL_HINTS = [
    "uk", "u.k", "britain", "british", "england", "london", "scotland", "wales",
    "ireland", "irish", "france", "french", "paris", "germany", "german", "berlin",
    "europe", "european", "spain", "spanish", "italy", "italian", "netherlands",
    "dutch", "amsterdam", "belgium", "sweden", "swedish", "austria", "vienna",
    "greece", "greek", "athens", "thessaloniki", "poland", "polish", "russia",
    "russian", "ukraine", "australia", "australian", "sydney", "melbourne", "bondi",
    "canada", "canadian", "toronto", "montreal", "ottawa", "ontario", "quebec",
    "saskatoon", "argentina", "brazil", "brazilian", "mexico", "chile", "south africa",
    "new zealand", "switzerland", "swiss", "zurich", "geneva", "norway", "denmark",
    "finland", "hungary", "romania", "turkey",
]
_GLOBAL_RE = re.compile(r"\b(" + "|".join(re.escape(h) for h in _GLOBAL_HINTS) + r")\b")


def guess_region(candidate):
    text = (candidate["title"] + " " + candidate.get("source", "")).lower()
    return "Global" if _GLOBAL_RE.search(text) else "US"


def gather():
    seen_titles, seen_links = set(), set()
    candidates = []

    def news_url(q, recency):
        return ("https://news.google.com/rss/search?q="
                + urllib.parse.quote(q + " " + recency)
                + "&hl=en-US&gl=US&ceid=US:en")

    # (url, is_priority). Priority feeds first so their flag wins on de-dupe.
    sources = [(news_url('"' + q + '"', PRIORITY_RECENCY), True) for q in PRIORITY_QUERIES]
    sources += [(news_url(q, RECENCY), False) for q in QUERIES]
    sources += [(f, False) for f in DIRECT_FEEDS]

    now = time.time()
    for url, is_priority in sources:
        feed = _fetch(url)
        for e in feed.entries:
            link = getattr(e, "link", "").strip()
            title, source = _clean_title(getattr(e, "title", ""))
            if not link or not title:
                continue
            if not source:
                src = getattr(e, "source", None)
                source = getattr(src, "title", "") if src else ""
            # Hard recency gate — drop anything older than the age ceiling.
            pub = getattr(e, "published_parsed", None)
            max_age = PRIORITY_MAX_AGE_DAYS if is_priority else MAX_AGE_DAYS
            if pub is not None and (now - calendar.timegm(pub)) > max_age * 86400:
                continue
            key = _norm(title)
            if not key or key in seen_titles or link in seen_links:
                continue
            seen_titles.add(key)
            seen_links.add(link)
            candidates.append({
                "title": title,
                "source": source or "News",
                "link": link,
                "published": pub,
                "priority": is_priority,
            })

    # Most recent first; items without a date sink to the bottom.
    candidates.sort(key=lambda c: c["published"] or (), reverse=True)
    capped = candidates[:MAX_CANDIDATES]
    # Never let the candidate cap drop a priority item.
    extra = [c for c in candidates[MAX_CANDIDATES:] if c.get("priority")]
    return capped + extra


# ---------------------------------------------------------------------------
# Curate
# ---------------------------------------------------------------------------

def curate_llm(candidates):
    import anthropic

    client = anthropic.Anthropic()
    listing = "\n".join(
        f"[{i}] {'[FILITTI] ' if c.get('priority') else ''}{c['title']} ({c['source']})"
        for i, c in enumerate(candidates)
    )
    user = (
        "Here are the candidate headlines. Select and rank the in-scope stories and "
        "pick the siren.\n\n" + listing
    )

    with client.messages.stream(
        model=MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        system=SYSTEM,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        msg = stream.get_final_message()

    if msg.stop_reason == "refusal":
        raise RuntimeError("Model declined the request (refusal).")

    text = next(b.text for b in msg.content if b.type == "text")
    data = json.loads(text)

    n = len(candidates)
    def ok(i):
        return isinstance(i, int) and 0 <= i < n

    siren_i = data["siren_index"]
    if not ok(siren_i):
        raise RuntimeError("Model returned an out-of-range siren index.")

    siren = dict(candidates[siren_i])
    siren["headline"] = (data.get("siren_headline") or siren["title"]).strip()
    siren["region"] = data.get("siren_region") or guess_region(siren)

    seen, stories = {siren_i}, []
    for item in data.get("stories", []):
        i = item.get("index")
        if ok(i) and i not in seen:
            seen.add(i)
            c = dict(candidates[i])
            c["region"] = item.get("region") or guess_region(c)
            stories.append(c)
    return siren, stories


def curate_fallback(candidates):
    """Keyword-only selection when no API key is available."""
    scored = []
    for c in candidates:
        t = c["title"].lower()
        if not any(k in t for k in INCLUDE_KW):
            continue
        if any(k in t for k in EXCLUDE_KW):
            continue
        scored.append(c)
    scored = scored[:60]
    if not scored:
        return None, []
    siren = dict(scored[0])
    siren["headline"] = siren["title"]
    siren["region"] = guess_region(siren)
    stories = []
    for c in scored[1:]:
        d = dict(c)
        d["region"] = guess_region(d)
        stories.append(d)
    return siren, stories


# ---------------------------------------------------------------------------
# Priority names (enforced deterministically, regardless of curation path)
# ---------------------------------------------------------------------------

def _is_priority(c, prio_links):
    return c["link"] in prio_links or any(n in c["title"].lower() for n in PRIORITY_NAMES)


def apply_priority(siren, stories, candidates):
    """Float the priority stories the curator KEPT to the top; optionally siren one.

    We deliberately do NOT force in priority items the curator dropped: a search for a
    person's name also returns off-beat pieces that merely quote them, and the curator
    (or, in the fallback, the keyword filter) is what decides relevance. This only
    re-ranks the on-beat priority stories that already made the cut.
    """
    prio_links = {c["link"] for c in candidates if c.get("priority")}

    pool = ([siren] if siren else []) + list(stories)
    kept_prio = [c for c in pool if _is_priority(c, prio_links)]
    if not kept_prio:
        return siren, stories

    others = [c for c in pool if not _is_priority(c, prio_links)]

    if PRIORITY_AS_SIREN:
        new_siren = kept_prio[0]
        if not new_siren.get("headline"):          # was a story, not the siren
            new_siren = dict(new_siren)
            new_siren["headline"] = new_siren["title"]
        rest = kept_prio[1:] + others
    else:
        new_siren = siren
        rest = kept_prio + [c for c in others if not (siren and c["link"] == siren["link"])]

    if new_siren and not new_siren.get("region"):
        new_siren["region"] = guess_region(new_siren)

    seen = {new_siren["link"]} if new_siren else set()
    deduped = []
    for c in rest:
        if c["link"] not in seen:
            seen.add(c["link"])
            if not c.get("region"):
                c["region"] = guess_region(c)
            deduped.append(c)
    return new_siren, deduped


# ---------------------------------------------------------------------------
# Render (Drudge aesthetic: single column, <font> tags, no CSS, no JS)
# ---------------------------------------------------------------------------

LINK_COLOR = "#0018a8"    # dark, high-contrast blue for headline links
SIREN_COLOR = "#cc0000"   # red siren
TEXT_COLOR = "#111111"    # near-black body text
META_COLOR = "#555555"    # source names (darker than before, still secondary)


def link(text, url, color=LINK_COLOR):
    # Inline color with !important so an embedding site's theme can't gray it out.
    return (f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener" '
            f'style="color:{color} !important;text-decoration:underline;">'
            f'{html.escape(text)}</a>')


def _masthead(stamp):
    return [
        '<font face="Times New Roman, Times, serif" size="7"><b>JEW-HATRED TODAY</b></font>',
        "<br>",
        '<font face="Arial, Helvetica, sans-serif" size="1">'
        "TRACKING ANTISEMITISM AND ANTI-JEWISH HATE ACROSS THE DIASPORA</font>",
        "<br>",
        f'<font face="Arial, Helvetica, sans-serif" size="1">UPDATED {html.escape(stamp)}</font>',
        '<hr width="60%">',
    ]


def _siren_block(siren):
    if not siren:
        return []
    return [
        '<font face="Arial, Helvetica, sans-serif" size="5" color="#cc0000"><b>',
        "&#128680;&#128680;&#128680; "
        + link(siren["headline"].upper(), siren["link"], SIREN_COLOR)
        + " &#128680;&#128680;&#128680;",
        "</b></font>",
        "<br>",
        f'<font face="Arial, Helvetica, sans-serif" size="1">'
        f'<span style="color:{META_COLOR};">{html.escape(siren["source"])}</span></font>',
        '<hr width="60%">',
    ]


def _heading(text):
    return [
        f'<font face="Arial, Helvetica, sans-serif" size="3"><b>{html.escape(text)}</b></font>',
        '<hr width="40%">',
    ]


def _story_table(stories):
    out = ['<table width="100%" style="max-width:640px" border="0" cellpadding="0" '
           'cellspacing="0"><tr><td align="left">',
           '<font face="Times New Roman, Times, serif" size="4">']
    for s in stories:
        out.append(link(s["title"], s["link"])
                   + f' <font size="1"><span style="color:{META_COLOR};">'
                   f'({html.escape(s["source"])})</span></font>')
        out.append("<br><br>")
    out += ["</font>", "</td></tr></table>"]
    return out


def _footer():
    return [
        '<hr width="60%">',
        '<font face="Arial, Helvetica, sans-serif" size="1" color="#777777">'
        "Automated headline aggregation. Links open at their original publishers.</font>",
        "<br><br>",
    ]


# Wrap everything so text without its own color stays dark inside a host page's theme.
WRAP_OPEN = f'<div style="color:{TEXT_COLOR};">'
WRAP_CLOSE = "</div>"


def _content(siren, stories, stamp):
    """Flat single-column layout."""
    lines = [WRAP_OPEN, "<center>"] + _masthead(stamp) + _siren_block(siren) + _story_table(stories)
    lines += _footer() + ["</center>", WRAP_CLOSE]
    return "\n".join(lines)


def _content_sections(siren, stories, stamp):
    """US / Global sectioned layout."""
    us = [s for s in stories if s.get("region", "US") == "US"]
    intl = [s for s in stories if s.get("region", "US") != "US"]
    lines = [WRAP_OPEN, "<center>"] + _masthead(stamp) + _siren_block(siren)
    if us:
        lines += _heading("UNITED STATES") + _story_table(us)
    if intl:
        lines += _heading("GLOBAL") + _story_table(intl)
    lines += _footer() + ["</center>", WRAP_CLOSE]
    return "\n".join(lines)


def _wrap_full(content):
    return "\n".join([
        "<html>", "<head>", '<meta charset="utf-8">',
        "<title>JEW-HATRED TODAY</title>",
        # Classic Drudge auto-refresh (plain HTML, no JS): reload every 10 minutes.
        '<meta http-equiv="refresh" content="600">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "</head>",
        '<body bgcolor="#ffffff" text="#000000" link="#0000cc" vlink="#551a8b">',
        content,
        # Lets an embedding page auto-size its iframe to this content. Harmless when
        # the page is viewed directly (it just posts to a parent that isn't listening).
        '<script>(function(){function h(){try{parent.postMessage('
        '{jht:1,h:document.documentElement.scrollHeight},"*");}catch(e){}}'
        'window.addEventListener("load",h);window.addEventListener("resize",h);'
        'setInterval(h,1500);})();</script>',
        "</body>", "</html>",
    ])


def _wrap_embed(content, stamp):
    return f"<!-- Jew-hatred Today - generated {stamp} -->\n" + content


def render_full(siren, stories, stamp):
    return _wrap_full(_content(siren, stories, stamp))


def render_embed(siren, stories, stamp):
    return _wrap_embed(_content(siren, stories, stamp), stamp)


def render_full_sections(siren, stories, stamp):
    return _wrap_full(_content_sections(siren, stories, stamp))


def render_embed_sections(siren, stories, stamp):
    return _wrap_embed(_content_sections(siren, stories, stamp), stamp)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    candidates = gather()
    print(f"Gathered {len(candidates)} unique candidates.", file=sys.stderr)
    if not candidates:
        print("No candidates fetched; aborting.", file=sys.stderr)
        sys.exit(1)

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            siren, stories = curate_llm(candidates)
            print(f"LLM selected siren + {len(stories)} stories.", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 — keep the page building
            print(f"LLM curation failed ({exc}); using keyword fallback.", file=sys.stderr)
            siren, stories = curate_fallback(candidates)
    else:
        print("No ANTHROPIC_API_KEY; using keyword fallback.", file=sys.stderr)
        siren, stories = curate_fallback(candidates)

    # Enforce priority names (e.g., Gerard Filitti) regardless of the curation path.
    siren, stories = apply_priority(siren, stories, candidates)

    if not siren:
        print("Nothing in scope after curation; aborting.", file=sys.stderr)
        sys.exit(1)

    stamp = datetime.now(ZoneInfo("America/New_York")).strftime("%a %b %-d, %Y %-I:%M %p ET")
    out_dir = os.path.dirname(OUTPUT_PATH) or "."
    os.makedirs(out_dir, exist_ok=True)

    outputs = {
        OUTPUT_PATH: render_full(siren, stories, stamp),                       # flat, full page
        os.path.join(out_dir, "embed.html"): render_embed(siren, stories, stamp),          # flat fragment
        os.path.join(out_dir, "index_sections.html"): render_full_sections(siren, stories, stamp),   # sectioned, full
        os.path.join(out_dir, "embed_sections.html"): render_embed_sections(siren, stories, stamp),  # sectioned fragment
    }
    for path, content in outputs.items():
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)

    us = sum(1 for s in stories if s.get("region", "US") == "US")
    print(f"Wrote {len(outputs)} files: {len(stories) + 1} stories "
          f"({us} US / {len(stories) - us} Global) + siren.", file=sys.stderr)


if __name__ == "__main__":
    main()
