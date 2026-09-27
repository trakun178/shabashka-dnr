import type { Metadata } from "next";
import Link from "next/link";
import { getAdByTgId, getAllAdIds } from "@/lib/api";

const SITE = "https://shabashka.sofoniya.ru";
const FALLBACK_IMG = `${SITE}/images/logo.webp`;

type Props = { params: Promise<{ id: string }> };

// ✅ Без этой функции статический экспорт динамического маршрута невозможен
export async function generateStaticParams() {
  const rows = await getAllAdIds();
  return rows.map((r) => ({ id: String(r.tg_message_id) }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const ad = await getAdByTgId(id);
  if (!ad) return { title: "Объявление — Шабашка DNR" };

  const url = `${SITE}/ad/${ad.tg_message_id}/`;
  const image = ad.photo_url || FALLBACK_IMG;
  const description = (
    ad.description ||
    ad.title ||
    "Объявление Шабашка DNR"
  ).slice(0, 200);

  return {
    title: `${ad.title} — Шабашка DNR`,
    description,
    alternates: { canonical: url },
    openGraph: {
      type: "article",
      siteName: "Шабашка DNR",
      locale: "ru_RU",
      title: ad.title,
      description,
      url,
      images: [{ url: image, width: 1280, height: 960, alt: ad.title }],
    },
    twitter: {
      card: "summary_large_image",
      title: ad.title,
      description,
      images: [image],
    },
  };
}

export default async function AdPage({ params }: Props) {
  const { id } = await params;
  const ad = await getAdByTgId(id);
  if (!ad) return <main style={{ padding: 24 }}>Объявление не найдено.</main>;

  let photos: string[] = [];
  try {
    photos = JSON.parse(ad.photo_urls || "[]");
  } catch {
    photos = [];
  }
  if (!photos.length && ad.photo_url) photos = [ad.photo_url];

  return (
    <main style={{ maxWidth: 800, margin: "0 auto", padding: 16 }}>
      <h1>{ad.title}</h1>
      <p style={{ color: "#999" }}>
        📍 {ad.city} · 🗓 {new Date(ad.created_at).toLocaleString("ru-RU")}
      </p>
      {photos.map((src) => (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          key={src}
          src={src}
          alt={ad.title}
          style={{ width: "100%", borderRadius: 12, marginBottom: 12 }}
        />
      ))}
      <p style={{ whiteSpace: "pre-wrap", fontSize: 18 }}>{ad.description}</p>
      {ad.phone && (
        <p style={{ fontSize: 22, fontWeight: 700 }}>📞 {ad.phone}</p>
      )}
      <p>
        {ad.post_link && <a href={ad.post_link}>Открыть в Telegram</a>}
        {ad.post_link && ad.vk_post_url && " · "}
        {ad.vk_post_url && <a href={ad.vk_post_url}>Пост в VK</a>}
      </p>
      <p>
        <a href="/">← Все объявления</a>
      </p>
    </main>
  );
}
