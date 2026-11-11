import { describe, it, expect } from "vitest";
import app from "../index";
import { buildWhatsAppUrl, formatLeadNotification } from "../templates";

describe("Notifications Bot API Routes", () => {
  it("GET / returns 200 with text", async () => {
    const res = await app.request("http://localhost/");
    expect(res.status).toBe(200);
    const text = await res.text();
    expect(text).toContain("UG-Scripts Notifications Bot");
  });

  it("GET /health returns 200 with JSON payload", async () => {
    const res = await app.request("http://localhost/health", {}, {
      ADMIN_CHAT_ID: "123456",
      BOT_TOKEN: "mock-token",
    });
    expect(res.status).toBe(200);
    const data = (await res.json()) as Record<string, any>;
    expect(data.status).toBe("ok");
    expect(data.app).toBe("notifications-bot");
    expect(data.adminConfigured).toBe(true);
  });

  it("POST /notify rejects unauthorized requests when NOTIFY_SECRET is set", async () => {
    const res = await app.request(
      "http://localhost/notify",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: "Alice", phone: "123", company: "Test Corp" }),
      },
      {
        BOT_TOKEN: "mock-token",
        NOTIFY_SECRET: "super-secret",
        ADMIN_CHAT_ID: "123456",
      }
    );

    expect(res.status).toBe(401);
    const data = (await res.json()) as Record<string, any>;
    expect(data.error).toContain("Unauthorized");
  });

  it("POST /notify returns 503 if ADMIN_CHAT_ID is missing", async () => {
    const res = await app.request(
      "http://localhost/notify",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer super-secret",
        },
        body: JSON.stringify({ name: "Alice", phone: "123", company: "Test Corp" }),
      },
      {
        BOT_TOKEN: "mock-token",
        NOTIFY_SECRET: "super-secret",
      }
    );

    expect(res.status).toBe(503);
    const data = (await res.json()) as Record<string, any>;
    expect(data.error).toContain("ADMIN_CHAT_ID is not configured");
  });

  it("POST /notify returns 400 when payload is empty or invalid", async () => {
    const res = await app.request(
      "http://localhost/notify",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer super-secret",
        },
        body: JSON.stringify({}),
      },
      {
        BOT_TOKEN: "mock-token",
        NOTIFY_SECRET: "super-secret",
        ADMIN_CHAT_ID: "123456",
      }
    );

    expect(res.status).toBe(400);
    const data = (await res.json()) as Record<string, any>;
    expect(data.error).toContain("Payload must include name/phone/company or text");
  });
});

describe("Template & Helper Utilities", () => {
  it("formats lead notification with Dhaka GMT+6 timestamp", () => {
    const output = formatLeadNotification({
      name: "Tanvir",
      phone: "+8801712345678",
      company: "Dhaka Studio",
    });

    expect(output).toContain("Dhaka Time, GMT+6");
    expect(output).toContain("Tanvir");
    expect(output).toContain("+8801712345678");
    expect(output).toContain("Dhaka Studio");
  });

  it("builds WhatsApp URL with auto 88 prefix for 11-digit local numbers", () => {
    const url = buildWhatsAppUrl("01712345678", "Tanvir");
    expect(url).not.toBeNull();
    expect(url).toContain("https://wa.me/8801712345678");
    expect(url).toContain("Tanvir");
  });

  it("builds WhatsApp URL preserving international numbers", () => {
    const url = buildWhatsAppUrl("+1 (555) 234-5678", "Alice");
    expect(url).not.toBeNull();
    expect(url).toContain("https://wa.me/15552345678");
  });

  it("returns null for empty or invalid phone numbers", () => {
    expect(buildWhatsAppUrl("")).toBeNull();
    expect(buildWhatsAppUrl("abc")).toBeNull();
  });
});
