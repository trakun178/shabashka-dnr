export async function getAdByTgId(tgMessageId: string | number) {
  const res = await fetch(
    `${process.env.SUPABASE_URL}/rest/v1/ads?tg_message_id=eq.${tgMessageId}&limit=1`,
    {
      headers: {
        apikey: process.env.SUPABASE_KEY!,
        Authorization: `Bearer ${process.env.SUPABASE_KEY!}`,
      },
      next: { revalidate: 300 },
    },
  );
  if (!res.ok) return null;
  const rows = await res.json();
  return rows[0] ?? null;
}
