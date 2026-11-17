# Automated Multi-Platform Posting System

**Python / FastAPI practical assessment — Dxora Technologies**

A modular REST API that validates a short message with exactly one CTA URL and attempts to publish it **independently** to five real, documented provider APIs. There are no fake success responses in production code.

## What is implemented?

- Core submission endpoint: `POST http://localhost:4000/posting` (interactive documentation at `/docs`). Two **local OAuth2 setup routes** `/wordpress/connect` and `/wordpress/callback` are additionally required for WordPress.com; they do not publish content.
- Pydantic validation: 1–200 characters, exactly one syntactically valid HTTP(S) CTA URL, reject local/private addresses.
- Five separate integrations using `httpx`: **Mastodon, Bluesky, Telegram public channel, Discord webhook, WordPress**.
- Real authorization and provider HTTP requests. Credentials are provided via environment variables, never hard-coded.
- Concurrent attempts; the failure of one integration **does not stop** the others.
- Per-platform results: `platform`, `status`, `posted_url`, `public_access`, `date`, `time`, `error`.
- Safe failure results for missing credentials, rejected requests, or network issues.
- Tests covering validation, all five simulated API responses, disabled mode, failure isolation, missing configuration, link facets, and offline WordPress.com OAuth2 authorization/callback/posting flow.

**Evidence distinction:** The **29 automated tests** use mocked provider requests and do not publish live messages. **Separate** live tests were conducted using the applicant's authorized accounts on November 17, 2026, with links documented in `evidence/LIVE_VERIFICATION_SUMMARY.md`. Those separate tests confirmed real posts on all five platforms; this does **not** establish a single five-provider simultaneously successful API call. Discord channel messages generally require server access, so `public_access` is conservatively `false` for Discord even when its API successfully returns a message ID. This limitation is intentionally disclosed rather than reporting a private server link as globally public.

## Installation

Requires Python 3.10+ (Python 3.11+ recommended).

```bash
# from the root project folder
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Copy `.env.example` to `.env` and fill the **credentials of accounts and channels you own or administer**. Leave `POSTING_ENABLED=false` until you're ready to publish. Never share `.env` or upload it to a public repository.

```bash
# Linux/macOS
cp .env.example .env
# Windows PowerShell
Copy-Item .env.example .env
```

### Environment variables

| Provider | Variables | Configuration requirements |
|---|---|---|
| Mastodon | `MASTODON_BASE_URL`, `MASTODON_TOKEN` | HTTPS instance URL; user OAuth access token with `write:statuses` |
| Bluesky | `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD` | Bluesky username and dedicated app password |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_PUBLIC_CHANNEL` | Bot is channel admin with posting rights, public `@channelname` |
| Discord | `DISCORD_WEBHOOK_URL` | Webhook created for an authorized server channel |
| WordPress.com | `WORDPRESS_BASE_URL`, `WORDPRESS_CLIENT_ID`, `WORDPRESS_CLIENT_SECRET` | HTTPS WordPress.com site and an OAuth2 app (free plan supported); open `/wordpress/connect` once to authorize |
| Self-hosted WordPress | `WORDPRESS_BASE_URL`, `WORDPRESS_USERNAME`, `WORDPRESS_APP_PASSWORD` | Separate self-hosted WordPress installation with a revocable Application Password |

After the five accounts are configured, set `POSTING_ENABLED=true` in `.env` and restart the app. Sending the same request again may create duplicate posts; do not enable live publishing until you intend the side effect.

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Visit **http://localhost:4000/docs** and try the `POST /posting` endpoint.

### Example request

```bash
curl -X POST http://localhost:4000/posting \
  -H 'Content-Type: application/json' \
  -d '{"message":"Explore our business platform: https://example.com"}'
```

For Windows PowerShell, use:

```powershell
$body = @{ message = 'Explore our business platform: https://example.com' } | ConvertTo-Json
Invoke-RestMethod -Uri 'http://localhost:4000/posting' -Method Post -ContentType 'application/json' -Body $body
```

### Real response semantics

- `success=true` **only if all five providers successfully confirm publication**.
- A provider `status=success` means a provider's real API confirmed its send/post request and returned a post URL. Actual visibility may still depend on provider settings or moderation; `public_access` reports the known default visibility, not an independent anonymous-access audit.
- Missing credentials or `POSTING_ENABLED=false` returns five explicit `failed` entries. **This is not evidence of publishing**.
- Bad input returns HTTP 422 before any external call.
- `time` is the app's UTC processing time, with a `Z` suffix; it is not the provider's timestamp.

For example, with `POSTING_ENABLED=false`, the response begins:

```json
{
  "success": false,
  "results": [
    {
      "platform": "Mastodon",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Publishing disabled: set POSTING_ENABLED=true after configuring authorized accounts"
    }
  ]
}
```

There will be **five** `results` entries, one per provider.

## Run tests

```bash
python -m pytest -q
```

The **29 tests** use mocked provider transports and local ASGI application requests; they *do not* contact third-party websites. `evidence/TEST_RESULTS.txt` records the offline test results; live evidence is tracked separately. Offline results are clearly labeled **simulated**, never proof of public posts.

## Architecture

```text
dxora-automated-posting/
├── app/
│   ├── main.py                  # Single FastAPI POST endpoint
│   ├── schemas.py               # Validation and typed response fields
│   ├── config.py                # Environment-based configuration
│   ├── services/
│   │   └── posting_service.py   # Concurrent fan-out and error isolation
│   └── platforms/
│       ├── base.py              # Shared response/error logic
│       ├── mastodon.py          # OAuth status post
│       ├── bluesky.py           # AT Proto session + rich-text post
│       ├── telegram.py          # Telegram bot / public channel
│       ├── discord.py           # Webhook with wait=true
│       └── wordpress.py         # Public WordPress post
├── app/wordpress_oauth.py       # OAuth2 login & callback for WordPress.com
├── tests/test_posting.py
├── tests/test_wordpress_oauth.py
├── evidence/TEST_RESULTS.txt
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
└── README.md
```

## Integration and limitations

1. **Mastodon** — a public status is created with `POST /api/v1/statuses`; access token scope `write:statuses` is needed.
2. **Bluesky** — an app-password-backed session is created, then `com.atproto.repo.createRecord` publishes `app.bsky.feed.post`. A rich-text facet makes the CTA link clickable. This implementation uses the public Bluesky PDS endpoint at `bsky.social` (not custom PDS hosts).
3. **Telegram** — `sendMessage` publishes into a public channel the bot administers; a valid `t.me` link is constructed from the returned message ID. Private chat IDs are intentionally rejected.
4. **Discord** — execute a webhook with `wait=true`, inspect returned IDs, build a Discord message URL; most channels are not anonymously accessible, therefore `public_access=false`.
5. **WordPress** — WordPress.com uses browser-based OAuth2 Authorization Code Flow with CSRF `state` validation; access tokens are stored **locally in a Git-ignored file** and posts are published through `https://public-api.wordpress.com/rest/v1.2/sites/{site_id}/posts/new`. A site-ID and site-URL check prevents accidental posting to a different blog. Self-hosted WordPress can use a revocable Application Password through the site's `/wp-json` endpoint. The WordPress site must belong to the applicant or be administered with authorization.

External platforms may enforce permissions, rate limits, moderation, anti-spam rules, or API access restrictions. This program does not bypass these restrictions. Use it for legitimate announcements on channels you own or are permitted to operate. Because a live publish is irreversible on some platforms, do not rerun the same request without intending to create another post.

## Official API documentation

- Mastodon: https://docs.joinmastodon.org/methods/statuses/
- Bluesky / ATProto: https://docs.bsky.app/docs/advanced-guides/posts and https://docs.bsky.app/docs/api/com-atproto-repo-create-record
- Telegram Bot API: https://core.telegram.org/bots/api#sendmessage
- Discord Execute Webhook: https://docs.discord.com/developers/resources/webhook#execute-webhook
- WordPress.com OAuth2: https://developer.wordpress.com/docs/api/oauth2/
- WordPress.com create post: https://developer.wordpress.com/docs/api/getting-started/
- Self-hosted WordPress Application Passwords: https://developer.wordpress.org/advanced-administration/security/application-passwords/

## GitHub submission checklist

- [x] Source code, modular project structure, dependencies, example config, readme, and tests
- [x] Tests passing against mocked provider APIs
- [x] Applicant configured authorized provider credentials for separate live testing
- [x] Applicant ran separate legitimate live tests; reported URLs are in `evidence/LIVE_VERIFICATION_SUMMARY.md`
- [ ] Applicant adds scrubbed live screenshots or response logs to the repository if required
- [ ] Public GitHub repository is created and populated
- [ ] Repository URL and details are sent to `hr@chivoxai.com` by **22 November 2026**

**Do not claim all five services succeeded in one API request.** The applicant confirmed publication through separate live tests, including read-only verification of the existing Discord message; check the real links before submission.

> Note on the original assignment: its different sections mention 2 hours, 2–3 hours and 4 hours; its absolute delivery deadline is 22 November 2026. The only deadline on which this repository relies is 22 November.

### Windows scripts and English documentation

`01_SETUP_WINDOWS.bat` installs the local virtual environment; `02_RUN_TESTS_WINDOWS.bat` runs the offline test suite; `03_START_SERVER_WINDOWS.bat` starts the server. For other commands see `INSTALLATION_GUIDE.md`: `04_CONNECT_WORDPRESS_WINDOWS.bat`, `05_CHECK_NETWORK_WINDOWS.bat`, `06_TEST_SINGLE_PLATFORM_WINDOWS.bat`, and `07_VERIFY_EXISTING_DISCORD_MESSAGE_WINDOWS.bat`. The scripts never print account credentials. The single-platform live test performs a real post only after explicit `PUBLISH` confirmation.


## WordPress.com Free-Plan OAuth2 setup (Windows)

Read **`WORDPRESS_OAUTH_SETUP.md`** for complete English instructions.

1. Keep the existing `.env` private and add `WORDPRESS_BASE_URL=https://yourblog.wordpress.com`, `WORDPRESS_CLIENT_ID`, `WORDPRESS_CLIENT_SECRET` from your own registered WordPress.com developer application.
2. Match its OAuth2 redirect URL to **`http://localhost:4000/wordpress/callback`** (exactly).
3. Keep `POSTING_ENABLED=false` while authorizing. Start the app via `03_START_SERVER_WINDOWS.bat`, which binds **127.0.0.1** (local machine only).
4. Visit **`http://localhost:4000/wordpress/connect`**, approve access to your WordPress.com blog, and confirm the callback shows a successful connection.
5. The access token is saved in a hidden, **gitignored** local file `.wordpress_oauth_token.json`. Never commit or share this file, `.env`, or screenshots containing secrets.
6. After all five platforms are configured and you intend to publish, enable `POSTING_ENABLED=true`, restart FastAPI, and test `POST /posting` with one CTA link.

**Public visibility caveat:** `public_access=true` for WordPress signifies provider publication to a configured public site and should still be independently checked in a logged-out browser. Discord messages are usually not publicly accessible; disclose that limitation.

## Discord status and existing-message verification

Discord live posting succeeded in the user-managed server but the original client required `guild_id`, which is optional in the Discord Message response. The updated adapter retrieves guild metadata via read-only GET if needed. To confirm an existing webhook post without publishing again, run `07_VERIFY_EXISTING_DISCORD_MESSAGE_WINDOWS.bat` and paste its **message link** (not the channel link). Any proof is only genuine after a real GET confirmation. Keep `.env` and `.wordpress_oauth_token.json` outside version control. See `DISCORD_TROUBLESHOOTING.md` and `TESTING_AND_SUBMISSION.md`.
