# Testing, Evidence, and Submission

## Automated tests

Run `02_RUN_TESTS_WINDOWS.bat` on Windows or `python -m pytest -q` in an installed environment. The bundled suite contains **29 offline tests**, including FastAPI validation, failure isolation, WordPress OAuth and publishing, Discord verification, and Bluesky permalink handling. Mocked tests do not publish real messages.

## Existing live evidence (November 17, 2026)

The applicant has already completed separate live posting tests on Mastodon, Bluesky, Telegram, WordPress, and Discord. Discord's existing published message was independently confirmed by a read-only Discord webhook GET request. See `evidence/LIVE_VERIFICATION_SUMMARY.md` for links and important limitations. Do not claim the five platforms all succeeded in a single API request; the initial fan-out response was partially successful, and later individual retries verified the remaining providers.

## Safe local sequence

1. Back up your private local `.env` and `.wordpress_oauth_token.json`, but never include them in Git.
2. Set `POSTING_ENABLED=false` when you do not intend to publish, and restart the FastAPI server if you change the flag.
3. Use `05_CHECK_NETWORK_WINDOWS.bat` for reachability only; it never posts.
4. Use `07_VERIFY_EXISTING_DISCORD_MESSAGE_WINDOWS.bat` to verify an existing message without republishing.
5. Use `06_TEST_SINGLE_PLATFORM_WINDOWS.bat` **only** when an additional live WordPress or Discord post is truly necessary. It requires an explicit `PUBLISH` confirmation and targets a single selected platform.
6. Preserve relevant screenshots and local JSON records in `evidence/` after checking that no credential or secret appears in them.
7. Verify `python -m pytest -q` passes and inspect the public GitHub upload for any sensitive files.

## Publish to GitHub

Create a **public** repository, e.g. `dxora-automated-posting`. Upload the English source, tests, README, and sanitized evidence. Do not include `.env`, `.wordpress_oauth_token.json`, `.venv`, webhook URLs with embedded tokens, or secret-bearing screenshots. The distributable English ZIP intentionally contains no live credentials.

## Submit to Dxora Technologies

Send an email to **hr@chivoxai.com** with subject **Yunus Emre Atiklik - Python Practical test review**. Include:

- Public GitHub repository URL.
- Full name, contact number, and current city/country.
- Preferred date/time for a final-round interview, with timezone.
- A brief and accurate statement that live publications were separately verified, plus a note that Discord links usually are not public to anonymous users.

**Deadline: November 22, 2026.**
