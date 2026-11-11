# Sprint 5: Telegram Bot Notifications (`notifications-bot`)

## Overview
Adds an edge-native Telegram notifications microservice deployed on Cloudflare Workers using **grammY** and **Hono**.

## Architecture & Integration
- **Edge Runtime**: Cloudflare Workers (`ugscripts-notifications-bot`)
- **Internal Webhook**: `POST /notify` receives lead request alerts dispatched from `apps/api/auth.py`.
- **Security**: Protected with `Authorization: Bearer <NOTIFY_SECRET>`.
- **Interactive Actions**: Displays lead details formatted in Asia/Dhaka (+6) time, accompanied by an inline Telegram button that directly opens a prefilled WhatsApp chat with the requester's number.
- **Telegram Updates**: `POST /webhook` handles incoming commands (`/start`, `/id`, `/status`).
- **Bot Info Optimization**: Inlines static `BOT_INFO` in `wrangler.toml` to eliminate runtime `getMe` HTTP calls on cold starts.

## Useful Commands
```bash
# Start local bot dev server
bun run dev:bot

# Run vitest test suite
bun run test:bot

# Deploy to Cloudflare Workers
bun run deploy:bot
```
