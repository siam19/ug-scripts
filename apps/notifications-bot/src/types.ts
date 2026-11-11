export interface Env {
  BOT_TOKEN: string;
  BOT_INFO?: string;
  ADMIN_CHAT_ID?: string;
  NOTIFY_SECRET?: string;
  TELEGRAM_SECRET_TOKEN?: string;
}

export interface LeadNotificationPayload {
  name?: string;
  phone?: string;
  company?: string;
  content?: string;
  text?: string;
}
