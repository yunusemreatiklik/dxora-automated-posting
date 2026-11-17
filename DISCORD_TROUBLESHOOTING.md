# Discord Webhook Delivery and Existing-Message Verification

During a November 17, 2026 live test, the `DxoraPosting` webhook published a message to the authorized `Emre Tech Projects / #dxora-posting` channel. An earlier adapter incorrectly returned `failed` because it required `guild_id`, which is optional in a Discord Message response. The current adapter accepts the required message and channel identifiers and uses a read-only webhook metadata request to obtain the guild ID when available.

## Verify an existing message without publishing again

1. Make sure the computer can securely reach `https://discord.com` (a system-wide VPN connection may be needed on restricted networks).
2. In Discord, open the channel and right-click the **existing** message sent by `DxoraPosting`.
3. Choose **Copy Message Link** (do not copy the channel link).
4. Double-click **`07_VERIFY_EXISTING_DISCORD_MESSAGE_WINDOWS.bat`**.
5. Paste the message URL and press Enter. The tool sends only a read-only `GET /webhooks/{webhook.id}/{webhook.token}/messages/{message.id}` request and checks its identifiers and expected message content.
6. When successful, it writes `evidence/LIVE_discord_verified_existing_message.json` to the local project directory. Review this JSON for private information before deciding whether to upload it.

**Never rerun live publishing merely to verify an already posted Discord message.** The public accessibility of a Discord server message is not guaranteed; therefore `public_access=false` remains correct.

### SSL / network troubleshooting

A hostname mismatch or an untrusted certificate is a connection problem, not proof that publishing failed. Validate DNS and TLS before trying again. Do not disable certificate verification with `verify=False` or `curl -k`, and do not include Discord webhook tokens in screenshots or public output. Rotate any previously exposed webhook token.

Discord API reference: https://discord.com/developers/docs/resources/webhook#get-webhook-message
