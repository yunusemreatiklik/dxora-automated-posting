# WordPress.com OAuth2 Setup — Windows

The project supports WordPress.com free-plan sites using browser-based OAuth2. Self-hosted WordPress can alternatively use Application Passwords.

1. Register an application at https://developer.wordpress.com/apps/ for a WordPress.com site you own. The application name can be `DxoraPosting`.
2. Set its exact redirect URL to **`http://localhost:4000/wordpress/callback`**.
3. In your *private local* `.env`, configure the site URL, WordPress.com Client ID and Client Secret:

```ini
WORDPRESS_BASE_URL=https://yourblog.wordpress.com
WORDPRESS_CLIENT_ID=YOUR_CLIENT_ID
WORDPRESS_CLIENT_SECRET=YOUR_CLIENT_SECRET
POSTING_ENABLED=false
```

4. Double-click `01_SETUP_WINDOWS.bat` if dependencies are not installed.
5. Start `03_START_SERVER_WINDOWS.bat`; leave the window open.
6. Double-click `04_CONNECT_WORDPRESS_WINDOWS.bat`, or enter `http://localhost:4000/wordpress/connect` manually.
7. Sign in to WordPress.com and authorize the application for the intended site.
8. The callback should display **WordPress.com connection successful!** No access token is printed on the page.
9. The access token is stored locally in `.wordpress_oauth_token.json`, which is ignored by Git. Never commit it.
10. With proper authorization, live WordPress publishing uses WordPress.com's `POST /rest/v1.2/sites/{site_id}/posts/new` API. Do not enable global live posting merely to confirm OAuth.

## Troubleshooting

- `Fill WORDPRESS_CLIENT_ID...`: missing `.env` values or server not restarted.
- `Invalid/expired OAuth state`: open `/wordpress/connect` again; authorization state is single-use.
- Token exchange/network error: check the WordPress application settings, the exact redirect URL, and the network.
- Site mismatch: make sure `WORDPRESS_BASE_URL` matches the blog authorized through OAuth.
- `HTTP 403`: posting permissions were rejected; check the application authorization and the endpoint. This is not a successful publication.

The project also retains a separate Application Password mode for independently hosted WordPress installations. Its credentials are not used by WordPress.com OAuth2.
