# Withings Token Guardian MCP

A standalone microservice that manages Withings OAuth token refresh via webhook.

## Purpose

This service acts as a "guardian" for the Withings MCP, automatically refreshing OAuth tokens when they expire. When the Withings MCP detects a 401 error, it calls this service's webhook endpoint to trigger a token refresh.

## Architecture

```
Withings MCP (detects 401)
    ↓
Calls Token Guardian webhook
    ↓
Token Guardian:
  - Calls Withings MCP /admin/token/refresh
  - Returns success/failure
    ↓
Withings MCP retries with new token
```

## Endpoints

### `GET /`
Health check endpoint

### `GET /health`
Detailed health check with configuration status

### `POST /webhook/refresh-needed`
Webhook endpoint called by Withings MCP when 401 error occurs

**Headers:**
- `X-Guardian-Secret`: Secret token for authentication

**Response:**
```json
{
  "success": true,
  "message": "Token refreshed successfully",
  "expires_at": "2025-12-31T08:14:39+00:00",
  "timestamp": "2025-12-31T05:30:00+00:00"
}
```

### `POST /refresh`
Manual token refresh endpoint for testing

**Headers:**
- `X-Admin-Token`: Admin API token

## Environment Variables

### Required

- `WITHINGS_MCP_URL` - URL of Withings MCP service (e.g., `https://withings-mcp-production.up.railway.app`)
- `ADMIN_API_TOKEN` - Admin API token for calling Withings MCP refresh endpoint
- `GUARDIAN_SECRET` - Secret token for webhook authentication (generate with `openssl rand -hex 32`)

### Optional

- `PORT` - Port to run on (default: 8081)
- `RAILWAY_TOKEN` - Railway API token (future use for direct env var updates)
- `RAILWAY_PROJECT_ID` - Railway project ID (future use)
- `RAILWAY_SERVICE_ID` - Withings MCP service ID (future use)

## Deployment to Railway

### 1. Create New Service

1. Go to your Railway project
2. Click "+ New"
3. Select "GitHub Repo"
4. Choose `Orchid1970/withings-token-guardian`
5. Railway will auto-detect the Dockerfile and deploy

### 2. Configure Environment Variables

Add these variables in Railway:

```bash
WITHINGS_MCP_URL=https://withings-mcp-production.up.railway.app
ADMIN_API_TOKEN=<copy from Withings MCP service>
GUARDIAN_SECRET=<generate new: openssl rand -hex 32>
```

### 3. Get Guardian URL

After deployment, Railway will provide a URL like:
```
https://withings-token-guardian-production.up.railway.app
```

### 4. Update Withings MCP

Add environment variable to Withings MCP service:

```bash
GUARDIAN_WEBHOOK_URL=https://withings-token-guardian-production.up.railway.app/webhook/refresh-needed
GUARDIAN_SECRET=<same secret from step 2>
```

## Testing

### Test Manual Refresh

```bash
curl -X POST https://withings-token-guardian-production.up.railway.app/refresh \
  -H "X-Admin-Token: YOUR_GUARDIAN_SECRET"
```

### Test Webhook

```bash
curl -X POST https://withings-token-guardian-production.up.railway.app/webhook/refresh-needed \
  -H "X-Guardian-Secret: YOUR_GUARDIAN_SECRET"
```

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export WITHINGS_MCP_URL=http://localhost:8080
export ADMIN_API_TOKEN=your_token
export GUARDIAN_SECRET=your_secret

# Run
python main.py
```

## How It Works

1. Withings MCP makes API request to Withings
2. Withings returns 401 (token expired)
3. Withings MCP calls Token Guardian webhook
4. Token Guardian calls Withings MCP `/admin/token/refresh`
5. Withings MCP refreshes token from Withings OAuth
6. Token Guardian returns success
7. Withings MCP retries original request with new token
8. ✅ Request succeeds!

## Advantages

✅ **Separation of concerns** - Token management isolated from data fetching
✅ **Resilience** - Independent service with independent logs
✅ **Security** - Webhook authentication prevents unauthorized refresh
✅ **Monitoring** - Dedicated logs for token operations
✅ **Scalability** - Can manage tokens for multiple services
✅ **Flexibility** - Easy to extend for other health APIs

## Future Enhancements

- Direct Railway API integration to update environment variables
- Support for multiple health service tokens (Fitbit, Oura, etc.)
- Proactive refresh scheduler (refresh before expiration)
- Metrics and monitoring dashboard
- Slack/Discord notifications on refresh failures

## License

MIT
