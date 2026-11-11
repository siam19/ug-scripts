export function formatLeadNotification(data: {
  name: string;
  phone: string;
  company: string;
}): string {
  const escape = (str: string) =>
    str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

  const timestamp = new Date().toLocaleString("en-US", {
    timeZone: "Asia/Dhaka",
    dateStyle: "medium",
    timeStyle: "short",
  });

  return [
    `🎯 <b>New Demo Access Request</b>`,
    ``,
    `👤 <b>Name:</b> ${escape(data.name || "N/A")}`,
    `📞 <b>Phone:</b> ${escape(data.phone || "N/A")}`,
    `🏢 <b>Company:</b> ${escape(data.company || "N/A")}`,
    ``,
    `🕒 <i>${escape(timestamp)} (Dhaka Time, GMT+6)</i>`,
  ].join("\n");
}

/**
 * Builds a direct WhatsApp chat link (wa.me) with an optional prefilled greeting.
 * Handles local Bangladesh format (01XXXXXXXXX) by prepending country code 88.
 */
export function buildWhatsAppUrl(phone: string, name?: string): string | null {
  if (!phone) return null;
  let digits = phone.replace(/[^0-9]/g, "");
  if (!digits || digits.length < 7) return null;

  // Prepend Bangladesh country code 88 if entered as local 11-digit mobile number
  if (digits.startsWith("01") && digits.length === 11) {
    digits = "88" + digits;
  }

  const cleanName = name?.trim();
  const greeting = cleanName ? `Hi ${cleanName}, ` : "Hi, ";
  const text = `${greeting}thanks for requesting access to UG-Scripts! Here is your access code: `;

  return `https://wa.me/${digits}?text=${encodeURIComponent(text)}`;
}
