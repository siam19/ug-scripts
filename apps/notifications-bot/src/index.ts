import { Hono } from "hono";
import { InlineKeyboard, webhookCallback } from "grammy";
import { createBot } from "./bot";
import { buildWhatsAppUrl, formatLeadNotification } from "./templates";
import type { Env, LeadNotificationPayload } from "./types";

const app = new Hono<{ Bindings: Env }>();

function extractPhoneFromText(text?: string): string | undefined {
  if (!text) return undefined;
  const match = text.match(/Phone\*?:?\s*([+0-9\s-]{8,20})/i);
  return match ? match[1] : undefined;
}

app.get("/", (c) => {
  return c.text("UG-Scripts Notifications Bot is running on Cloudflare Workers.");
});

app.get("/health", (c) => {
  return c.json({
    status: "ok",
    app: "notifications-bot",
    adminConfigured: Boolean(c.env.ADMIN_CHAT_ID),
    timestamp: new Date().toISOString(),
  });
});

// Internal webhook to dispatch lead notifications (invoked by apps/api)
app.post("/notify", async (c) => {
  const env = c.env;

  // Verify secret token if NOTIFY_SECRET is set on the worker
  if (env.NOTIFY_SECRET) {
    const authHeader = c.req.header("Authorization");
    const secretHeader = c.req.header("X-Notify-Secret");
    const bearerToken = authHeader?.startsWith("Bearer ")
      ? authHeader.slice(7).trim()
      : null;

    const providedSecret = bearerToken || secretHeader;
    if (providedSecret !== env.NOTIFY_SECRET) {
      return c.json({ error: "Unauthorized. Invalid or missing secret." }, 401);
    }
  }

  const adminChatId = env.ADMIN_CHAT_ID?.trim();
  if (!adminChatId) {
    return c.json(
      { error: "ADMIN_CHAT_ID is not configured on the worker." },
      503
    );
  }

  let body: LeadNotificationPayload;
  try {
    body = await c.req.json<LeadNotificationPayload>();
  } catch {
    return c.json({ error: "Invalid JSON payload." }, 400);
  }

  let messageText: string;
  let parseMode: "HTML" | "Markdown" = "HTML";

  if (body.name || body.phone || body.company) {
    messageText = formatLeadNotification({
      name: body.name || "N/A",
      phone: body.phone || "N/A",
      company: body.company || "N/A",
    });
    parseMode = "HTML";
  } else if (body.text || body.content) {
    messageText = (body.text || body.content)!;
    parseMode = "Markdown";
  } else {
    return c.json(
      { error: "Payload must include name/phone/company or text." },
      400
    );
  }

  // Build inline WhatsApp action button if phone number is available
  const rawPhone = body.phone || extractPhoneFromText(body.text || body.content);
  let replyMarkup: InlineKeyboard | undefined;
  if (rawPhone) {
    const waUrl = buildWhatsAppUrl(rawPhone, body.name);
    if (waUrl) {
      replyMarkup = new InlineKeyboard().url("💬 Message on WhatsApp", waUrl);
    }
  }

  const bot = createBot(env);

  try {
    const sent = await bot.api.sendMessage(adminChatId, messageText, {
      parse_mode: parseMode,
      reply_markup: replyMarkup,
    });
    return c.json({ success: true, messageId: sent.message_id });
  } catch (err: any) {
    console.error("Failed to send Telegram message:", err);
    return c.json(
      { error: "Failed to deliver Telegram message", details: err?.message },
      502
    );
  }
});

// Telegram Webhook endpoint (updates from Telegram servers)
app.post("/webhook", async (c) => {
  const env = c.env;
  if (!env.BOT_TOKEN) {
    return c.json({ error: "BOT_TOKEN not configured." }, 500);
  }

  const bot = createBot(env);
  const handleUpdate = webhookCallback(bot, "hono", {
    secretToken: env.TELEGRAM_SECRET_TOKEN,
  });

  return handleUpdate(c);
});

export default app;
