const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_KEY!;

const headers = {
  apikey: SUPABASE_KEY,
  Authorization: `Bearer ${SUPABASE_KEY}`,
};

export async function getAdByTgId(tgMessageId: string | number) {
  const res = await fetch(
    `${SUPABASE_URL}/rest/v1/ads?tg_message_id=eq.${tgMessageId}&limit=1`,
    { headers },
  );
  if (!res.ok) return null;
  const rows = await res.json();
  return rows[0] ?? null;
}

export async function getAllAdIds() {
  const res = await fetch(
    `${SUPABASE_URL}/rest/v1/ads?select=tg_message_id&order=tg_message_id.desc&limit=2000`,
    { headers },
  );
  if (!res.ok) return [];
  return (await res.json()) as { tg_message_id: number }[];
}

export async function getAllAds(limit = 1000): Promise<any[]> {
  const res = await fetch(
    `${SUPABASE_URL}/rest/v1/ads?order=tg_message_id.desc&limit=${limit}`,
    { headers },
  );
  if (!res.ok) return [];
  return res.json();
}

export async function getAdsByCategory(
  category: string,
  limit = 200,
): Promise<any[]> {
  const res = await fetch(
    `${SUPABASE_URL}/rest/v1/ads?category=eq.${encodeURIComponent(category)}&order=tg_message_id.desc&limit=${limit}`,
    { headers },
  );
  if (!res.ok) return [];
  return res.json();
}
