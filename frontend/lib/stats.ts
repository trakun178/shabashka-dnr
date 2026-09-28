import { TG_CHANNEL_ID, VK_GROUP_ID_NUM } from "@/lib/site";

export async function getTgMembers(): Promise<number | null> {
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
    if (!res.ok) return null;
    const rows = await res.json();
    return rows?.[0]?.tg_members ?? null;
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
