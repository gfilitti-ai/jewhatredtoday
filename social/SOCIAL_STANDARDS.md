# Social Post Standards — Gerard Filitti (personal account)

The standard for turning headlines from the aggregator feed into personal social posts.

## Account & framing
- Posts go out on Gerard's **personal** account. **No Jew-Hatred Today branding, no website, no outlet logos.**
- Format is Gerard's **own commentary on the article**, not a headline announcement.
- Platforms: **X and Instagram.** (Not LinkedIn.)

## Voice
- Follow the `filitti-voice` skill. Verdict-first, exact numbers, single hyphens (no em dashes), no exclamation points, every rhetorical question answered.
- Facts get verified against a primary source before posting; unconfirmed figures are flagged, never guessed.

## Asset — headline-hero card (THE STANDARD)
- Generator: `card_template.py` in this folder. 1080x1080 (works for X and IG).
- **The article headline is the hero:** serif (Caladea Bold), dark ink on white, styled like a news clipping, with a red `SOURCE | DATE` kicker above it.
- **Dark panel below** carries `GERARD FILITTI` and his one-line statement (Lato Black, white). Statement is optional — omit for a headline-only card.
- **No quotation marks.** No branding. Clean.
- Palette: ink `#141A`, red `#D62027`, dark panel `#14161C`.

## Packet section order (per story)
Heading, source line, headline-hero card, X copy, then the **article URL** for that post (plain clickable text, labeled "Article URL:"), then the **X hashtags** (the article URL comes immediately before the hashtags), then the Instagram caption, then the VERIFIED note.

## Hashtags (X — also fine on Instagram)
- **Never use `#NeverAgain`.**
- `#Antisemitism` — use freely.
- `#EndJewHatred` — use occasionally, not every post.
- Otherwise tailor to the story (e.g., `#IRGC`, `#Iran`, `#UK`, `#France`, `#HateCrimes`).

## Output location & filenames
- All deliverables (the .docx packet and every card PNG) go in **`~/Downloads/Claude-Social Media/`**. Do not write render byproducts or temp files there.
- **Every output filename must carry a run timestamp `YYYY-MM-DD-HHMM` (ET)** so nothing ever overwrites a previous file. Examples: `card_uk_irgc_2026-07-14-0805.png`, `Social Post Drafts - Personal - 2026-07-14-0805.docx`. This applies to anything that would otherwise share a name.

## Schedule
- Runs automatically at **10:00 AM and 3:00 PM ET daily** (scheduled task `social-post-drafts`).

## On-demand: single URL -> post
- When Gerard drops in an article URL, build a post from just that article (no feed needed): read the article (use the Chrome connection for paywalled sites like NYT, where his logged-in session sees the full text), verify the facts, then produce the X post + Instagram caption + hashtags + a headline-hero card, with the article URL as the reply.
- **Default action: stage as an X thread draft** (same as the batches) - never publish unless Gerard says "publish this one" for that specific post.
- Save the card (and any packet) into `~/Downloads/Claude-Social Media/` with a timestamped filename.

## X staging (unattended)
- After building the packet, each selected story is staged as an X **thread draft**: main post = commentary + hashtags + headline-hero card; second post (reply) = the article URL. Saved as a draft, **never published**.
- If Chrome is closed, not logged into X, or the composer can't be reached, staging stops without posting, the packet is still saved, and Gerard is notified which stories are pending so he can reconnect and re-run the task.

## Workflow (human-in-the-loop for now)
1. Read the live feed (SIREN + top stories).
2. Draft X post + Instagram caption in Gerard's voice; add X hashtags.
3. Generate a headline-hero card per post via `card_template.py`.
4. Assemble a review packet (.docx). **Nothing auto-posts** until Gerard approves.
