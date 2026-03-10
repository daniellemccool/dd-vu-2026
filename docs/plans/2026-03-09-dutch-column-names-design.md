# Dutch Column Names — Design Document

**Date:** 2026-03-09
**Branch:** chore/dutch-column-names
**Goal:** Migrate all participant-facing DataFrame column headers to Dutch, consistent with the column language policy. Column names are shown directly in the consent UI (not via `Translatable`) so they must be Dutch at the DataFrame level.

---

## Scope

All platform extraction files in `packages/python/port/platforms/`. One commit per platform, all in a single PR from `chore/dutch-column-names` → `master`.

`validate_received.py` column name entries updated in the same commit as each platform. Known missing-column issues in `validate_received.py` (X: `Account id`, `URL`; others) are **out of scope** — those require real-DDP validation runs.

**Platforms:** LinkedIn, X, Instagram, Chrome, YouTube, TikTok, Facebook
**Already correct:** Facebook is mostly Dutch; fix remaining English columns only.

---

## Translation Policy

- Translate where a natural Dutch equivalent exists
- Leave pure English proper nouns and technical loanwords unchanged: `Tweet`, `URL`, `Link`, `Account`, `Type`
- Use `Datum en tijd` for timestamps (consistent with existing Facebook/X usage)

---

## Shared Glossary

| English | Dutch |
|---------|-------|
| Date | Datum |
| Timestamp | Datum en tijd |
| Time | Tijd |
| Title | Titel |
| Name | Naam |
| Message | Bericht |
| Count | Aantal |
| Setting | Instelling |
| Method | Methode |
| Link | Link *(unchanged)* |
| URL | URL *(unchanged)* |
| Type | Type *(unchanged)* |

---

## Per-Platform Column Mappings

### LinkedIn (`linkedin.py`)

| Table | Current | Dutch |
|-------|---------|-------|
| linkedin_ads_clicked | Ad clicked Date | Advertentiedatum |
| linkedin_ads_clicked | Ad Title/Id | Advertentietitel/id |
| linkedin_comments | Date | Datum |
| linkedin_comments | Link | Link |
| linkedin_comments | Message | Bericht |
| linked_in_company_follows | Organization | Organisatie |
| linked_in_company_follows | Followed On | Gevolgd op |
| linkedin_shares | Date | Datum |
| linkedin_shares | ShareLink | Gedeelde link |
| linkedin_shares | ShareCommentary | Gedeelde tekst |
| linkedin_shares | SharedUrl | Gedeelde URL |
| linkedin_shares | MediaUrl | Media-URL |
| linkedin_shares | Visibility | Zichtbaarheid |
| linkedin_reactions | Date | Datum |
| linkedin_reactions | Type | Type |
| linkedin_reactions | Link | Link |
| linkedin_connections | First Name | Voornaam |
| linkedin_connections | Last Name | Achternaam |
| linkedin_connections | Email Address | E-mailadres |
| linkedin_connections | Company | Bedrijf |
| linkedin_connections | Position | Functie |
| linkedin_connections | Connected On | Verbonden op |
| linkedin_search_queries | Time | Tijd |
| linkedin_search_queries | Search Query | Zoekterm |

### X (`x.py`)

| Table | Current | Dutch |
|-------|---------|-------|
| x_follower | Account id | Account-id |
| x_follower | Link to user | Link naar gebruiker |
| x_following | Account id | Account-id |
| x_following | Link to user | Link naar gebruiker |
| x_block | Blocked users | Geblokkeerde gebruikers |
| x_like | Tweet Id | Tweet-id |
| x_like | URL | URL |
| x_like | Tweet | Tweet |
| x_tweet | Date | Datum |
| x_tweet | Tweet | Tweet |
| x_tweet | Retweeted | Geretweet |
| x_tweet_headers | Tweet id | Tweet-id |
| x_tweet_headers | User id | Gebruiker-id |
| x_tweet_headers | Created at | Aangemaakt op |
| x_ad_engagement | Impression time | Vertoonstijdstip |
| x_ad_engagement | Display location | Weergavelocatie |
| x_ad_engagement | Tweet text | Tweet-tekst |
| x_ad_engagement | Advertiser | Adverteerder |
| x_ad_engagement | Advertiser handle | Adverteerder-account |
| x_ad_engagement | Engagement type | Interactietype |
| x_ad_engagement | Engagement time | Interactietijd |
| x_personalization | Interest | Interesse |
| x_personalization | is disabled | Uitgeschakeld |
| x_mute | Account id | Account-id |
| x_mute | Link to user | Link naar gebruiker |
| x_user_link_clicks | Tweet id | Tweet-id |
| x_user_link_clicks | Link | Link |
| x_user_link_clicks | Datum en tijd | Datum en tijd *(already Dutch)* |

### Instagram (`instagram.py`)

| Table | Current | Dutch |
|-------|---------|-------|
| instagram_followers | Account | Account |
| instagram_followers | Link | Link |
| instagram_followers | Date | Datum |
| instagram_following | Account | Account |
| instagram_following | Link | Link |
| instagram_following | Date | Datum |
| instagram_posts_viewed | Author | Auteur |
| instagram_posts_viewed | Date | Datum |
| instagram_videos_watched | Author | Auteur |
| instagram_videos_watched | Date | Datum |
| instagram_liked_posts | Account name | Accountnaam |
| instagram_liked_posts | Value | Waarde |
| instagram_liked_posts | Link | Link |
| instagram_liked_posts | Date | Datum |
| instagram_profile_searches | Timestamp | Datum en tijd |
| instagram_profile_searches | Name | Naam |
| instagram_saved_posts | Title | Titel |
| instagram_saved_posts | Href | URL |
| instagram_saved_posts | Timestamp | Datum en tijd |

### Chrome (`chrome.py`)

| Table | Current | Dutch |
|-------|---------|-------|
| chrome_browser_history | Title | Titel |
| chrome_browser_history | Url | URL |
| chrome_browser_history | Transition | Transitietype |
| chrome_browser_history | Date | Datum |
| chrome_bookmarks | Bookmark | Bladwijzer |
| chrome_bookmarks | Url | URL |
| chrome_omnibox | Title | Titel |
| chrome_omnibox | Number of visits | Aantal bezoeken |
| chrome_omnibox | Url | URL |

### YouTube (`youtube.py`)

| Table | Current | Dutch |
|-------|---------|-------|
| youtube_watch_history | Title | Titel |
| youtube_watch_history | URL | URL |
| youtube_watch_history | Timestamp | Datum en tijd |
| youtube_search_history | Title | Titel |
| youtube_search_history | URL | URL |
| youtube_search_history | Timestamp | Datum en tijd |
| youtube_search_history | Ad | Advertentie |
| youtube_subscriptions | Channel Id | Kanaal-id |
| youtube_subscriptions | Channel Url | Kanaal-URL |
| youtube_subscriptions | Channel Title | Kanaalnaam |

### TikTok (`tiktok.py`)

| Table | Current | Dutch |
|-------|---------|-------|
| tiktok_watch_history | Date | Datum |
| tiktok_watch_history | Link | Link |
| tiktok_favorite_videos | Date | Datum |
| tiktok_favorite_videos | Link | Link |
| tiktok_follower | Date | Datum |
| tiktok_follower | UserName | Gebruikersnaam |
| tiktok_following | Date | Datum |
| tiktok_following | UserName | Gebruikersnaam |
| tiktok_hashtag | HashtagName | Hashtagnaam |
| tiktok_hashtag | HashtagLink | Hashtag-link |
| tiktok_like_list | Date | Datum |
| tiktok_like_list | Link | Link |
| tiktok_searches | Date | Datum |
| tiktok_searches | SearchTerm | Zoekterm |
| tiktok_share_history | Date | Datum |
| tiktok_share_history | SharedContent | Gedeelde inhoud |
| tiktok_share_history | Link | Link |
| tiktok_share_history | Method | Methode |
| tiktok_comments | Date | Datum |
| tiktok_comments | Comment | Reactie |
| tiktok_comments | Photo | Foto |
| tiktok_comments | Url | URL |
| tiktok_activity_summary | Metric | Metriek |
| tiktok_activity_summary | Count | Aantal |
| tiktok_settings | Setting | Instelling |
| tiktok_settings | Keywords | Trefwoorden |

### Facebook (`facebook.py`)

Only tables with remaining English columns:

| Table | Current | Dutch |
|-------|---------|-------|
| facebook_who_youve_followed | Name | Naam |
| facebook_who_youve_followed | Timestamp | Datum en tijd |
| facebook_news_your_locations | Location | Locatie |
| facebook_notifications | Text | Tekst |
| facebook_notifications | Link | Link |
| facebook_recently_viewed | Watched | Bekeken |
| facebook_recently_viewed | Name | Naam |
| facebook_recently_viewed | Link | Link |
| facebook_recently_viewed | Date | Datum |
| facebook_recently_visited | Watched | Bekeken |
| facebook_recently_visited | Name | Naam |
| facebook_recently_visited | Link | Link |
| facebook_recently_visited | Date | Datum |
| facebook_profile_update_history | Title | Titel |
| facebook_profile_update_history | Timestamp | Datum en tijd |
| facebook_likes_and_reactions | Reaction | Reactie |
| facebook_likes_and_reactions | Name | Naam |
| facebook_likes_and_reactions | URL | URL |
| facebook_likes_and_reactions | Timestamp | Datum en tijd |
| facebook_likes_and_reactions_titled | Title | Titel |
| facebook_likes_and_reactions_titled | Reaction | Reactie |
| facebook_likes_and_reactions_titled | Timestamp | Datum en tijd |
| facebook_your_group_membership_activity | Title | Titel |
| facebook_your_group_membership_activity | Group name | Groepsnaam |
| facebook_your_group_membership_activity | Timestamp | Datum en tijd |
| facebook_pages_and_profiles_you_follow | Title | Titel |
| facebook_pages_and_profiles_you_follow | Timestamp | Datum en tijd |
| facebook_pages_youve_liked | Name | Naam |
| facebook_pages_youve_liked | Url | URL |
| facebook_pages_youve_liked | Timestamp | Datum en tijd |
| facebook_your_posts_and_check_ins | Title | Titel |
| facebook_your_posts_and_check_ins | Timestamp | Datum en tijd |

---

## Implementation Approach

**One commit per platform** in `chore/dutch-column-names`, each updating:
1. The platform extraction file (`port/platforms/<platform>.py`)
2. The matching entries in `tests/validate_received.py`

**Order:** LinkedIn → X → Instagram → Chrome → YouTube → TikTok → Facebook

**No new tests required** — column names are string constants; existing extraction logic is unchanged. The full test suite (`poetry run pytest`) must pass after each commit.

---

## validate_received.py Scope

Update only the column name entries that correspond to renamed columns. Do **not** add missing columns (`Account id`, `URL` in X schemas etc.) — those require real-DDP validation runs.

---

## D3I Compatibility Note

Column names are participant-facing UI strings, not part of the postMessage protocol. This change has no impact on compatibility with Eyra's mono or D3I's mono.
