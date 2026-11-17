# Installation Guide — Windows

This guide explains how to run the Dxora FastAPI multi-platform posting assessment. All project scripts, console prompts, and documentation are in English.

## Requirements

- Windows 10/11 and Python 3.10 or later (Python 3.12 supported).
- Internet access for dependency installation, WordPress OAuth authorization, and live API connections.
- Authorized access to your own Mastodon, Bluesky, Telegram, Discord, and WordPress accounts or channels.

## Setup

1. Extract the complete project into a new folder, for example `C:\Users\CASPER\Desktop\DXORA_ENGLISH`.
2. If you have already configured an earlier version, copy **only your own local** `.env` and `.wordpress_oauth_token.json` files into the new folder. These files are NOT included in the download.
3. Double-click **`01_SETUP_WINDOWS.bat`**. This creates `.venv` and installs the dependencies. It will not overwrite an existing `.env` file.
4. If you are starting from scratch, edit `.env` and enter your authorized API credentials. Keep `POSTING_ENABLED=false` until you intentionally want to publish.
5. Double-click **`02_RUN_TESTS_WINDOWS.bat`**. The expected clean-source result is `29 passed` (mocked/offline tests; no new posts).
6. Double-click **`03_START_SERVER_WINDOWS.bat`** and keep its terminal window open.
7. Open **`http://127.0.0.1:4000/docs`** in your browser (type the address directly; no extra characters).
8. For WordPress.com, double-click **`04_CONNECT_WORDPRESS_WINDOWS.bat`** if you have not already authorized the site.

## Windows script reference

| File | Purpose | Side effects |
| --- | --- | --- |
| `01_SETUP_WINDOWS.bat` | Install dependencies and initialize local `.env` | Local installation only |
| `02_RUN_TESTS_WINDOWS.bat` | Execute 29 mocked Python tests | No external posting |
| `03_START_SERVER_WINDOWS.bat` | Start FastAPI at `127.0.0.1:4000` | No posting on startup |
| `04_CONNECT_WORDPRESS_WINDOWS.bat` | Open browser-based WordPress OAuth authorization | Authorizes a site, does not publish |
| `05_CHECK_NETWORK_WINDOWS.bat` | Check reachability of Discord and WordPress | Read-only network requests |
| `06_TEST_SINGLE_PLATFORM_WINDOWS.bat` | Choose WordPress or Discord and send one test message | **LIVE POST** after typing `PUBLISH` |
| `07_VERIFY_EXISTING_DISCORD_MESSAGE_WINDOWS.bat` | Verify a previously published Discord message | Read-only, **no new post** |

## API examples

With the server running, open `/docs`, expand **POST /posting**, select **Try it out**, and enter:

```json
{"message": "Explore my engineering projects: https://github.com/yunusemreatiklik"}
```

Do not click **Execute** with `POSTING_ENABLED=true` unless you want to send this text to all five providers. Previous successful posts are not automatically deduplicated.

## Security and publication notes

- Never upload `.env`, `.wordpress_oauth_token.json`, `.venv`, API keys, app passwords, or webhook tokens to GitHub.
- Tokens shared in any chat, screenshot, or public log should be rotated before using the accounts for future work.
- Preserve existing live-post evidence; do **not** republish just to prove an already successful integration.
- Discord server messages normally require membership. `public_access=false` is expected even when the webhook post succeeds.
- Python tests simulate the third-party APIs; separately collected live links are listed in `evidence/LIVE_VERIFICATION_SUMMARY.md`.

## Delivery

Public GitHub repository and the submission email to `hr@chivoxai.com` with subject `Yunus Emre Atiklik - Python Practical test review`. Include your full name, GitHub repository URL, telephone, location, and preferred final-round interview time. Deadline: **November 22, 2026**.
