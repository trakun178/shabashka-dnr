// Хендл канала для Telegram Bot API — объявляем прямо здесь,
// чтобы не зависеть от имён в site.ts
const TG_CHANNEL_HANDLE = "@dnrsabbath";

export async function getTgMembers(): Promise<number | null> {
  // 1) Из БД: парсер пишет tg_members каждые 15 минут
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
  } catch {
    // тихо продолжаем к фолбэку
  }
  // 2) Фолбэк: прямой запрос в Telegram во время сборки
  const token = process.env.TELEGRAM_BOT_TOKEN;
  if (!token) return null;
  try {
    const res = await fetch(
      `https://api.telegram.org/bot${token}/getChatMemberCount?chat_id=${encodeURIComponent(TG_CHANNEL_HANDLE)}`,
    );
    if (!res.ok) return null;
    const j = await res.json();
    return j?.ok && typeof j.result === "number" ? j.result : null;
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

export async function getMaxMembers(): Promise<number | null> {
  // MAX не имеет открытого API — возвращаем null, плашка просто скрывается
  return null;
}
