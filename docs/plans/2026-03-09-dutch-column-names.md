# Dutch Column Names Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rename all participant-facing DataFrame column headers to Dutch across all platform extraction files.

**Architecture:** One commit per platform. Each commit updates the platform extraction file and the matching entries in `tests/validate_received.py` (only LinkedIn and X have schemas there). Column renames are applied via `df.rename(columns={...})` immediately after DataFrame construction — no logic changes, string constants only. No new tests are needed; run `poetry run pytest -v` after each platform to confirm no regressions.

**Tech Stack:** Python 3.11, pandas, pytest + poetry. Working directory: `packages/python/`.

**Design doc:** `docs/plans/2026-03-09-dutch-column-names-design.md`

---

## Background

Column headers are shown directly to participants in the consent UI — they are NOT passed through the `Translatable` system. They must be Dutch at the DataFrame level. `validate_received.py` is a personal validation tool (not shipped); update the column name entries but do NOT add missing columns (out of scope).

Run all commands from `packages/python/` unless stated otherwise.

---

## Task 1: LinkedIn

**Files:**
- Modify: `packages/python/port/platforms/linkedin.py`
- Modify: `packages/python/tests/validate_received.py`

### Step 1: Read the file

Read `packages/python/port/platforms/linkedin.py` in full to locate every DataFrame construction for each of the 7 tables.

### Step 2: Apply renames

For each table, add `df = df.rename(columns={...})` immediately after the DataFrame is constructed (or update the `columns=` argument directly if columns are set as a list). Apply these mappings:

**linkedin_ads_clicked:**
```python
{"Ad clicked Date": "Advertentiedatum", "Ad Title/Id": "Advertentietitel/id"}
```

**linkedin_comments:**
```python
{"Date": "Datum", "Message": "Bericht"}
# "Link" stays as "Link"
```

**linked_in_company_follows:**
```python
{"Organization": "Organisatie", "Followed On": "Gevolgd op"}
```

**linkedin_shares:**
```python
{
    "Date": "Datum",
    "ShareLink": "Gedeelde link",
    "ShareCommentary": "Gedeelde tekst",
    "SharedUrl": "Gedeelde URL",
    "MediaUrl": "Media-URL",
    "Visibility": "Zichtbaarheid",
}
```

**linkedin_reactions:**
```python
{"Date": "Datum"}
# "Type" and "Link" stay unchanged
```

**linkedin_connections:**
```python
{
    "First Name": "Voornaam",
    "Last Name": "Achternaam",
    "Email Address": "E-mailadres",
    "Company": "Bedrijf",
    "Position": "Functie",
    "Connected On": "Verbonden op",
}
```

**linkedin_search_queries:**
```python
{"Time": "Tijd", "Search Query": "Zoekterm"}
```

### Step 3: Update validate_received.py

In `packages/python/tests/validate_received.py`, update the `"linkedin"` entry in `SCHEMAS` (around line 51):

```python
"linkedin": {
    "linkedin_ads_clicked":      {"Advertentiedatum", "Advertentietitel/id"},
    "linkedin_comments":         {"Datum", "Link", "Bericht"},
    "linked_in_company_follows": {"Organisatie", "Gevolgd op"},
    "linkedin_shares":           {"Datum", "Gedeelde link", "Gedeelde tekst",
                                  "Gedeelde URL", "Media-URL", "Zichtbaarheid"},
    "linkedin_reactions":        {"Datum", "Type", "Link"},
    "linkedin_search_queries":   {"Tijd", "Zoekterm"},
},
```

### Step 4: Run tests

```bash
cd packages/python && poetry run pytest -v
```

Expected: all tests pass (no assertion failures, no import errors).

### Step 5: Commit

```bash
git add packages/python/port/platforms/linkedin.py \
        packages/python/tests/validate_received.py
git commit -m "chore: Dutch column names for LinkedIn"
```

---

## Task 2: X

**Files:**
- Modify: `packages/python/port/platforms/x.py`
- Modify: `packages/python/tests/validate_received.py`

### Step 1: Read the file

Read `packages/python/port/platforms/x.py` in full to locate all DataFrame constructions.

### Step 2: Apply renames

**x_follower** and **x_following** and **x_mute** (same mapping):
```python
{"Account id": "Account-id", "Link to user": "Link naar gebruiker"}
```

**x_block:**
```python
{"Blocked users": "Geblokkeerde gebruikers"}
```

**x_like:**
```python
{"Tweet Id": "Tweet-id"}
# "URL" and "Tweet" stay unchanged
```

**x_tweet:**
```python
{"Date": "Datum", "Retweeted": "Geretweet"}
# "Tweet" stays unchanged
```

**x_tweet_headers:**
```python
{"Tweet id": "Tweet-id", "User id": "Gebruiker-id", "Created at": "Aangemaakt op"}
```

**x_ad_engagement:**
```python
{
    "Impression time": "Vertoonstijdstip",
    "Display location": "Weergavelocatie",
    "Tweet text": "Tweet-tekst",
    "Advertiser": "Adverteerder",
    "Advertiser handle": "Adverteerder-account",
    "Engagement type": "Interactietype",
    "Engagement time": "Interactietijd",
}
```

**x_personalization:**
```python
{"Interest": "Interesse", "is disabled": "Uitgeschakeld"}
```

**x_user_link_clicks:** already has Dutch "Datum en tijd" — rename `Tweet id` only:
```python
{"Tweet id": "Tweet-id"}
# "Link" and "Datum en tijd" are already correct
```

### Step 3: Update validate_received.py

Update the `"x"` entry in `SCHEMAS`:

```python
"x": {
    "x_follower":      {"Link naar gebruiker"},
    "x_following":     {"Link naar gebruiker"},
    "x_block":         {"Geblokkeerde gebruikers"},
    "x_like":          {"Tweet-id", "Tweet"},
    "x_tweet":         {"Datum", "Tweet", "Geretweet"},
    "x_tweet_headers": {"Tweet-id", "Gebruiker-id", "Aangemaakt op"},
},
```

Note: `Account-id` is intentionally absent from the X schemas — it was already missing before this migration (known gap, not in scope to fix here).

### Step 4: Run tests

```bash
cd packages/python && poetry run pytest -v
```

Expected: all tests pass.

### Step 5: Commit

```bash
git add packages/python/port/platforms/x.py \
        packages/python/tests/validate_received.py
git commit -m "chore: Dutch column names for X"
```

---

## Task 3: Instagram

**Files:**
- Modify: `packages/python/port/platforms/instagram.py`

(Instagram has no schema in `validate_received.py` — no changes needed there.)

### Step 1: Read the file

Read `packages/python/port/platforms/instagram.py` in full.

### Step 2: Apply renames

**instagram_followers** and **instagram_following:**
```python
{"Date": "Datum"}
# "Account" and "Link" stay unchanged
```

**instagram_posts_viewed** and **instagram_videos_watched:**
```python
{"Author": "Auteur", "Date": "Datum"}
```

**instagram_liked_posts:**
```python
{"Account name": "Accountnaam", "Value": "Waarde", "Date": "Datum"}
# "Link" stays unchanged
```

**instagram_profile_searches:**
```python
{"Timestamp": "Datum en tijd", "Name": "Naam"}
```

**instagram_saved_posts:**
```python
{"Title": "Titel", "Href": "URL", "Timestamp": "Datum en tijd"}
```

### Step 3: Run tests

```bash
cd packages/python && poetry run pytest -v
```

Expected: all tests pass.

### Step 4: Commit

```bash
git add packages/python/port/platforms/instagram.py
git commit -m "chore: Dutch column names for Instagram"
```

---

## Task 4: Chrome

**Files:**
- Modify: `packages/python/port/platforms/chrome.py`

(Chrome has no schema in `validate_received.py`.)

### Step 1: Read the file

Read `packages/python/port/platforms/chrome.py` in full.

### Step 2: Apply renames

**chrome_browser_history:**
```python
{"Title": "Titel", "Url": "URL", "Transition": "Transitietype", "Date": "Datum"}
```

**chrome_bookmarks:**
```python
{"Bookmark": "Bladwijzer", "Url": "URL"}
```

**chrome_omnibox:**
```python
{"Title": "Titel", "Number of visits": "Aantal bezoeken", "Url": "URL"}
```

### Step 3: Run tests

```bash
cd packages/python && poetry run pytest -v
```

Expected: all tests pass.

### Step 4: Commit

```bash
git add packages/python/port/platforms/chrome.py
git commit -m "chore: Dutch column names for Chrome"
```

---

## Task 5: YouTube

**Files:**
- Modify: `packages/python/port/platforms/youtube.py`

(YouTube has no schema in `validate_received.py`.)

### Step 1: Read the file

Read `packages/python/port/platforms/youtube.py` in full.

### Step 2: Apply renames

**youtube_watch_history** and **youtube_search_history** (both use same base columns):
```python
{"Title": "Titel", "Timestamp": "Datum en tijd"}
# "URL" stays unchanged
```

**youtube_search_history** additionally:
```python
{"Ad": "Advertentie"}
```

**youtube_subscriptions:**
```python
{"Channel Id": "Kanaal-id", "Channel Url": "Kanaal-URL", "Channel Title": "Kanaalnaam"}
```

Note: YouTube normalises column names explicitly (e.g. `df.columns = ["Channel Id", "Channel Url", "Channel Title"]`). Update the string literals in those assignments directly rather than adding a rename.

### Step 3: Run tests

```bash
cd packages/python && poetry run pytest -v
```

Expected: all tests pass.

### Step 4: Commit

```bash
git add packages/python/port/platforms/youtube.py
git commit -m "chore: Dutch column names for YouTube"
```

---

## Task 6: TikTok

**Files:**
- Modify: `packages/python/port/platforms/tiktok.py`

(TikTok has no schema in `validate_received.py`.)

### Step 1: Read the file

Read `packages/python/port/platforms/tiktok.py` in full.

### Step 2: Apply renames

**tiktok_watch_history** and **tiktok_favorite_videos** and **tiktok_like_list:**
```python
{"Date": "Datum"}
# "Link" stays unchanged
```

**tiktok_follower** and **tiktok_following:**
```python
{"Date": "Datum", "UserName": "Gebruikersnaam"}
```

**tiktok_hashtag:**
```python
{"HashtagName": "Hashtagnaam", "HashtagLink": "Hashtag-link"}
```

**tiktok_searches:**
```python
{"Date": "Datum", "SearchTerm": "Zoekterm"}
```

**tiktok_share_history:**
```python
{
    "Date": "Datum",
    "SharedContent": "Gedeelde inhoud",
    "Method": "Methode",
}
# "Link" stays unchanged
```

**tiktok_comments:**
```python
{"Date": "Datum", "Comment": "Reactie", "Photo": "Foto", "Url": "URL"}
```

**tiktok_activity_summary:**
```python
{"Metric": "Metriek", "Count": "Aantal"}
```

**tiktok_settings:**
```python
{"Setting": "Instelling", "Keywords": "Trefwoorden"}
```

### Step 3: Run tests

```bash
cd packages/python && poetry run pytest -v
```

Expected: all tests pass.

### Step 4: Commit

```bash
git add packages/python/port/platforms/tiktok.py
git commit -m "chore: Dutch column names for TikTok"
```

---

## Task 7: Facebook

**Files:**
- Modify: `packages/python/port/platforms/facebook.py`

(Facebook has no schema in `validate_received.py`.)

### Step 1: Read the file

Read `packages/python/port/platforms/facebook.py` in full. Facebook is already mostly Dutch — only fix the remaining English columns listed below.

### Step 2: Apply renames (English-only tables)

**facebook_who_youve_followed:**
```python
{"Name": "Naam", "Timestamp": "Datum en tijd"}
```

**facebook_news_your_locations:**
```python
{"Location": "Locatie"}
```

**facebook_notifications** (fix English columns only — Dutch ones already correct):
```python
{"Text": "Tekst"}
# "Link", "Gelezen", "Datum" — check which are already Dutch and skip those
```

**facebook_recently_viewed** and **facebook_recently_visited:**
```python
{"Watched": "Bekeken", "Name": "Naam", "Date": "Datum"}
# "Link" stays unchanged
```

**facebook_profile_update_history:**
```python
{"Title": "Titel", "Timestamp": "Datum en tijd"}
```

**facebook_likes_and_reactions:**
```python
{"Reaction": "Reactie", "Name": "Naam", "Timestamp": "Datum en tijd"}
# "URL" stays unchanged
```

**facebook_likes_and_reactions_titled:**
```python
{"Title": "Titel", "Reaction": "Reactie", "Timestamp": "Datum en tijd"}
```

**facebook_your_group_membership_activity:**
```python
{"Title": "Titel", "Group name": "Groepsnaam", "Timestamp": "Datum en tijd"}
```

**facebook_pages_and_profiles_you_follow:**
```python
{"Title": "Titel", "Timestamp": "Datum en tijd"}
```

**facebook_pages_youve_liked:**
```python
{"Name": "Naam", "Url": "URL", "Timestamp": "Datum en tijd"}
```

**facebook_your_posts_and_check_ins:**
```python
{"Title": "Titel", "Timestamp": "Datum en tijd"}
```

### Step 3: Run tests

```bash
cd packages/python && poetry run pytest -v
```

Expected: all tests pass.

### Step 4: Commit

```bash
git add packages/python/port/platforms/facebook.py
git commit -m "chore: Dutch column names for Facebook"
```

---

## Final Verification

After all 7 tasks:

```bash
cd packages/python && poetry run pytest -v
cd packages/data-collector && pnpm build
```

Both must pass cleanly.

Then push the branch and open a PR:

```bash
git push -u origin chore/dutch-column-names
gh pr create --title "chore: migrate all platform column names to Dutch" \
  --base master
```
