import type { Metadata } from "next";
import Link from "next/link";

const SITE = "https://shabashka.sofoniya.ru";

const CATEGORIES = [
  "ремонт",
  "сантехника",
  "электрика",
  "строительство",
  "грузчики",
  "уборка",
  "окна",
  "другое",
];

type Props = { params: Promise<{ category: string }> };

export function generateStaticParams() {
  return CATEGORIES.map((category) => ({ category }));
}

async function getAds(category: string): Promise<any[]> {
  const url =
    `${process.env.NEXT_PUBLIC_SUPABASE_URL}/rest/v1/ads` +
    `?category=eq.${encodeURIComponent(category)}&order=created_at.desc&limit=100`;
  const res = await fetch(url, {
    headers: {
      apikey: process.env.NEXT_PUBLIC_SUPABASE_KEY!,
      Authorization: `Bearer ${process.env.NEXT_PUBLIC_SUPABASE_KEY!}`,
    },
  });
  if (!res.ok) return [];
  return res.json();
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { category } = await params;
  const title = `Объявления — ${category} | Шабашка DNR`;
  const description = `Свежие объявления в категории «${category}»: Донецк, Макеевка, ДНР.`;
  return {
    title,
    description,
    openGraph: { title, description, url: `${SITE}/category/${category}/` },
  };
}

export default async function CategoryPage({ params }: Props) {
  const { category } = await params;
  const ads = await getAds(category);

  return (
    <main style={{ maxWidth: 800, margin: "0 auto", padding: 16 }}>
      <h1>Объявления: {category}</h1>
      {ads.length === 0 && <p>В этой категории пока пусто.</p>}
      {ads.map((ad: any) => (
        <article
          key={ad.tg_message_id}
          style={{ borderBottom: "1px solid #333", padding: "12px 0" }}
        >
          <h2 style={{ fontSize: 18 }}>
            <Link
              href={`/ad/${ad.tg_message_id}/`}
              style={{ color: "inherit" }}
            >
              {ad.title}
            </Link>
          </h2>
          <p style={{ color: "#999", margin: "4px 0" }}>
            📍 {ad.city}
            {ad.phone ? ` · 📞 ${ad.phone}` : ""}
          </p>
          {ad.photo_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={ad.photo_url}
              alt={ad.title}
              style={{
                width: "100%",
                maxHeight: 300,
                objectFit: "cover",
                borderRadius: 12,
              }}
            />
          )}
        </article>
      ))}
      <p style={{ marginTop: 16 }}>
        <Link href="/">← Все объявления</Link>
      </p>
    </main>
  );
}
