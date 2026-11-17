# Live Integration Verification — November 17, 2026

**Origin of evidence:** API results and screenshots collected on the applicant's own Windows computer. The URLs below correspond to real posts reported and demonstrated during that session. These are **separate live tests**, not a claim that all five platforms succeeded in a single `POST /posting` call.

| Provider | Result | Evidence URL | Accessibility note |
| --- | --- | --- | --- |
| Mastodon | Published | https://mastodon.social/@emreatiklik/117632838389139558 | Reported public |
| Bluesky | Published | https://bsky.app/profile/emreatiklik.bsky.social/post/3n2jj7oov4k2e | Corrected permalink; reported public |
| Telegram | Published | https://t.me/emre_dxora_demo/2 | Public channel |
| WordPress.com | Published | https://emreatiklik.wordpress.com/2026/11/17/dxora-python-integration-verification-on-wordpress-2/ | Public site |
| Discord | Published and subsequently confirmed by a read-only webhook GET | https://discord.com/channels/1572184900696674354/1572186549238632519/1572310737768939734 | **Not necessarily public:** server membership may be required |

The first combined FastAPI test returned successes for Mastodon, Bluesky, and Telegram but failures for Discord (network error) and WordPress (403). Following configuration fixes, WordPress published successfully and Discord delivered a message. The first Discord post was initially misreported as failed because the adapter expected an optional `guild_id`; the updated adapter fixes that reporting logic. A separate read-only verification of the existing Discord message later reported `status=success`, `error=null`, and `public_access=false`.

**Limitations:** Provider links and screenshots should be checked again before formal submission. This summary does not include secrets or credentials, and an automated test pass does not substitute for live proof. A single fan-out run with five simultaneous successes has **not** been demonstrated.
