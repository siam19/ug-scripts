import { Bot, Context } from "grammy";
import type { UserFromGetMe } from "grammy/types";
import type { Env } from "./types";

export function createBot(env: Env): Bot<Context> {
  const options: { botInfo?: UserFromGetMe } = {};
  if (env.BOT_INFO) {
    try {
      options.botInfo = JSON.parse(env.BOT_INFO);
    } catch (e) {
      console.warn("Could not parse BOT_INFO:", e);
    }
  }

  const bot = new Bot<Context>(env.BOT_TOKEN, options);

  bot.command("start", async (ctx) => {
    const from = ctx.from;
    const chatId = ctx.chat?.id;
    const name = from?.first_name || "there";

    const msg = [
      `👋 <b>Welcome to UG-Scripts Notification Bot!</b>`,
      ``,
      `Hello ${name}! This bot delivers instant notifications whenever a user submits an access request for UG-Scripts.`,
      ``,
      `🔑 <b>Your Telegram Chat ID:</b> <code>${chatId}</code>`,
      ``,
      `To receive lead notifications in this chat, set this ID in your Cloudflare Worker:`,
      `<code>bunx wrangler secret put ADMIN_CHAT_ID</code>`,
      ``,
      `<b>Available Commands:</b>`,
      `• /id - Show your Telegram user and chat ID`,
      `• /status - Check bot connection and admin configuration status`,
    ].join("\n");

    await ctx.reply(msg, { parse_mode: "HTML" });
  });

  bot.command("id", async (ctx) => {
    const chatId = ctx.chat?.id;
    const userId = ctx.from?.id;
    await ctx.reply(
      `🆔 <b>Telegram Info</b>\n• <b>Chat ID:</b> <code>${chatId}</code>\n• <b>User ID:</b> <code>${userId}</code>`,
      { parse_mode: "HTML" }
    );
  });

  bot.command("status", async (ctx) => {
    const currentChatId = String(ctx.chat?.id);
    const configuredAdminId = env.ADMIN_CHAT_ID?.trim();
    const isAdmin = configuredAdminId ? configuredAdminId === currentChatId : false;

    const msg = [
      `⚙️ <b>UG-Scripts Notification Bot Status</b>`,
      `• <b>Runtime:</b> Cloudflare Workers (Edge)`,
      `• <b>Admin Chat:</b> ${configuredAdminId ? "Configured" : "⚠️ Not configured"}`,
      `• <b>Your Status:</b> ${isAdmin ? "✅ Configured Admin" : "ℹ️ Non-admin chat"}`,
      `• <b>Webhook Target:</b> <code>POST /notify</code>`,
    ].join("\n");

    await ctx.reply(msg, { parse_mode: "HTML" });
  });

  return bot;
}
