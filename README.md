# Off the beaten track? A holistic and inclusive approach to exploring how people encounter and interpret political information

Data donation workflow for the VU Amsterdam 2026 study, led by Tim Groot Kormelink (VU Amsterdam, starting November 2025). Built on the [D3I data-donation-task](https://github.com/d3i-infra/data-donation-task) framework, which runs inside Eyra's Next platform.

Participants donate data exports from up to 7 platforms. For each platform they upload their data package, review what will be shared, and choose to donate or decline.

## Platforms and collected data

| Platform  | Tables |
|-----------|--------|
| LinkedIn  | `linkedin_ads_clicked`, `linkedin_comments`, `linked_in_company_follows`, `linkedin_shares`, `linkedin_reactions`, `linkedin_connections`, `linkedin_search_queries` |
| X         | `x_follower`, `x_following`, `x_block`, `x_like`, `x_tweet`, `x_tweet_headers`, `x_ad_engagement`, `x_personalization`, `x_mute`, `x_user_link_clicks` |
| Instagram | `instagram_followers`, `instagram_following`, `instagram_posts_viewed`, `instagram_videos_watched`, `instagram_liked_posts`, `instagram_profile_searches`, `instagram_saved_posts` |
| Chrome    | `chrome_browser_history`, `chrome_bookmarks`, `chrome_omnibox` |
| Facebook  | `facebook_who_youve_followed`, `facebook_news_your_locations`, `facebook_notifications`, `facebook_reels_usage`, `facebook_last_28`, `facebook_search_history`, `facebook_recently_viewed`, `facebook_recently_visited`, `facebook_profile_update_history`, `facebook_likes_and_reactions`, `facebook_likes_and_reactions_titled`, `facebook_your_group_membership_activity`, `facebook_pages_and_profiles_you_follow`, `facebook_pages_youve_liked`, `facebook_your_posts_and_check_ins`, `facebook_feed_controls`, `facebook_content_sharing_links_you_created`, `facebook_story_reactions` |
| YouTube   | `youtube_watch_history`, `youtube_search_history`, `youtube_subscriptions` |
| TikTok    | `tiktok_watch_history`, `tiktok_activity_summary`, `tiktok_settings`, `tiktok_favorite_videos`, `tiktok_follower`, `tiktok_following`, `tiktok_hashtag`, `tiktok_like_list`, `tiktok_searches`, `tiktok_share_history`, `tiktok_comments` |

Tables may be empty for a given participant if their export does not contain that data.

## Setup

Prerequisites: [Node.js](https://nodejs.org/en), [pnpm](https://pnpm.io/installation), [Python 3.11+](https://www.python.org/), [Poetry](https://python-poetry.org/)

```sh
pnpm install
pnpm run start    # builds Python package, starts dev server at http://localhost:3000
```

## Building releases

```sh
bash release.sh
```

Produces one zip per platform in `releases/`, named `dd-vu-2026_<Platform>_<branch>_<date>_<build>.zip`. Each zip is a self-contained build for a single platform.

## Deployment

This workflow supports two host platforms, configured via `packages/data-collector/.env.local` (copy from `.env.example`):

| Variable | Value | Platform |
|----------|-------|----------|
| `VITE_ASYNC_DONATIONS` | unset / `false` | D3I self-hosted mono (default) |
| `VITE_ASYNC_DONATIONS` | `true` | Eyra Next |

**D3I mono (default):** donations are fire-and-forget — the workflow posts data and continues immediately.

**Eyra Next:** as of January 2026, Eyra's platform stores donations via HTTP POST and sends back a `DonateSuccess` or `DonateError` reply over a MessageChannel. Setting `VITE_ASYNC_DONATIONS=true` enables the workflow to await that reply.

See `packages/data-collector/.env.example` for details.

## Citation

If you use this repository in your research, please cite it as follows:

```
@article{Boeschoten2023,
  doi = {10.21105/joss.05596},
  url = {https://doi.org/10.21105/joss.05596},
  year = {2023},
  publisher = {The Open Journal},
  volume = {8},
  number = {90},
  pages = {5596},
  author = {Laura Boeschoten and Niek C. de Schipper and Adriënne M. Mendrik and Emiel van der Veen and Bella Struminskaya and Heleen Janssen and Theo Araujo},
  title = {Port: A software tool for digital data donation},
  journal = {Journal of Open Source Software}
}
```

You can find the full citation details in the [`CITATION.cff`](CITATION.cff) file.
