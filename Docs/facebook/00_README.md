# Facebook / Meta API Documentation

Source: Meta Developer Docs (developers.facebook.com)
API Version: v22.0 (released Feb 2025, supported until Feb 2027)
Base URL: `https://graph.facebook.com/v22.0/`

---

## Files in This Folder

| File | Contents |
|------|----------|
| [01_graph_api_overview.md](01_graph_api_overview.md) | Core Graph API: versioning, nodes, edges, field syntax, pagination, batch requests, rate limits, error codes |
| [02_authentication.md](02_authentication.md) | OAuth 2.0 flow, all token types, long-lived exchange, debug_token, permissions list, appsecret_proof, security |
| [03_pages_api.md](03_pages_api.md) | Page node fields, all edges, feed/posts endpoints, post fields, publishing, permissions |
| [04_page_insights_api.md](04_page_insights_api.md) | All page-level metrics, post-level metrics, video metrics, messaging metrics, periods, breakdowns |
| [05_marketing_ads_api.md](05_marketing_ads_api.md) | Ad Account, Campaign, Ad Set, Ad nodes; Insights fields; breakdowns; async jobs; permissions |
| [06_instagram_graph_api.md](06_instagram_graph_api.md) | IG User/Media node fields, stories, reels, insights metrics, content publishing flow |
| [07_webhooks_errors_rate_limits.md](07_webhooks_errors_rate_limits.md) | Webhook setup/verification, page subscription fields, rate limit headers, all error codes |
| [08_business_manager_api.md](08_business_manager_api.md) | Business node, ad account/page management, system users, pixels, catalogs, agency/client relationships |

---

## Quick Reference

```
# Nodes
/{node-id}                          GET any object by ID
/me                                 Resolves to current token's user or page
/act_{ad-account-id}                Ad account node

# Common Edges
/{page-id}/feed                     Page timeline posts
/{page-id}/posts                    Posts by the page
/{page-id}/insights                 Page analytics metrics
/{page-id}/conversations            Messenger threads
/{post-id}/insights                 Post analytics
/{ig-user-id}/media                 Instagram posts
/{ig-user-id}/insights              Instagram account analytics
/act_{id}/campaigns                 Campaigns in ad account
/act_{id}/insights                  Ad account reporting

# Business Manager
/{business-id}/owned_ad_accounts    List ad accounts owned by business
/{business-id}/owned_pages          List pages owned by business
/{business-id}/system_users         List system users
/{business-id}/access_token         Generate system user token
/{ad-account-id}/assigned_users     Assign system user to ad account

# Auth
GET /v22.0/oauth/access_token       Exchange code or extend token
GET /v22.0/debug_token              Inspect/validate a token
GET /v22.0/me/accounts              List pages managed by user

# Versions
Current: v22.0   Previous: v21.0, v20.0, v19.0
```
