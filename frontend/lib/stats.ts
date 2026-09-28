import { TG_CHANNEL_ID, VK_GROUP_ID_NUM } from "@/lib/site";

export async function getTgMembers(): Promise<number | null> {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  if (!token) return null;
  try {
    const res = await fetch(
      `https://api.telegram.org/bot${token}/getChat?chat_id=${encodeURIComponent(TG_CHANNEL_ID)}`,
    );
    if (!res.ok) return null;
    const j = await res.json();
    return j?.ok ? (j.result.members_count as number) : null;
  } catch {
    return null;
  }
}

export async function getVkMembers(): Promise<number | null> {
  const token = process.env.VK_STAT_TOKEN;
  if (!token) return null;
  try {
    const res = await fetch(
      `https://api.vk.com/method/groups.getById?group_id=${VK_GROUP_ID_NUM}&fields=members_count&v=5.131&access_token=${token}`,
    );
    if (!res.ok) return null;
    const j = await res.json();
    return j?.response?.[0]?.members_count ?? null;
  } catch {
    return null;
  }
}
