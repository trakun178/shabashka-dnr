import { MAX_MEMBERS, MAX_CHANNEL } from "@/lib/site";

const TG_CHAT_ID = "@dnrsabbath"; // хендл канала именно для getChat

export async function getTgMembers(): Promise<number | null> {
  // 1) Читаем из БД — парсер пишет туда каждые 15 минут
  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_SUPABASE_URL}/rest/v1/parser_state?id=eq.1&select=tg_members`,
      {
        headers: {
          apikey: process.env.NEXT_PUBLIC_SUPABASE_KEY!,
          Authorization: `Bearer ${process.env.NEXT_PUBLIC_SUPABASE_KEY!}`,
        },
      },
    );
    if (res.ok) {
      const rows = await res.json();
      const v = rows?.[0]?.tg_members;
      if (typeof v === "number" && v > 0) return v;
    }
  } catch {}
  // 2) Фолбэк: прямой запрос в Telegram прямо во время сборки сайта
  const token = process.env.TELEGRAM_BOT_TOKEN;
  if (!token) return null;
  try {
    const res = await fetch(
      `https://api.telegram.org/bot${token}/getChat?chat_id=${encodeURIComponent(TG_CHAT_ID)}`,
    );
    if (!res.ok) return null;
    const j = await res.json();
    return j?.ok ? (j.result?.members_count ?? null) : null;
  } catch {
    return null;
  }
}

export async function getVkMembers(): Promise<number | null> {
  const token = process.env.VK_STAT_TOKEN;
  if (!token) return null;
  try {
    const res = await fetch(
      `https://api.vk.com/method/groups.getById?group_id=203412616&fields=members_count&v=5.131&access_token=${token}`,
    );
    if (!res.ok) return null;
    const j = await res.json();
    return j?.response?.[0]?.members_count ?? null;
  } catch {
    return null;
  }
}

function parseCount(raw: string): number | null {
  let s = raw.replace(/[\s\u00A0]/g, "").replace(",", ".");
  let mult = 1;
  if (/тыс|k/i.test(s)) {
    mult = 1000;
    s = s.replace(/[kKтыс.]/gi, "");
  } else if (/млн|m/i.test(s)) {
    mult = 1000000;
    s = s.replace(/[mMмлн.]/gi, "");
  }
  const n = parseFloat(s);
  return isNaN(n) ? null : Math.round(n * mult);
}

export async function getMaxMembers(): Promise<number | null> {
  // 1) Пытаемся прочитать число подписчиков прямо со страницы MAX-канала
  try {
    const res = await fetch(MAX_CHANNEL, {
      headers: { "User-Agent": "Mozilla/5.0" },
    });
    if (res.ok) {
      const html = await res.text();
      const m = html.match(
        /([\d\s\u00A0.,]+[KkMm]?(?:тыс|млн)?)\s*(?:подписчик|subscriber)/i,
      );
      if (m) {
        const n = parseCount(m[1]);
        if (n != null && n > 0) return n;
      }
    }
  } catch {}
  // 2) Фолбэк: константа из site.ts (или null — тогда плашка просто скрыта)
  return MAX_MEMBERS;
}
