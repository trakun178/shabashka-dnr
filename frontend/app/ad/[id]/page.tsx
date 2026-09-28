import type { Metadata } from "next";
import Link from "next/link";
import { getAdByTgId, getAllAdIds } from "@/lib/api";
import { SITE, LOGO } from "@/lib/site";
import {
  Header,
  Footer,
  btnTg,
  btnVk,
  chip,
  PlaceholderArt,
} from "@/components/ui";

type Props = { params: Promise<{ id: string }> };

export async function generateStaticParams() {
  const rows = await getAllAdIds();
  return rows.map((r) => ({ id: String(r.tg_message_id) }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const ad = await getAdByTgId(id);
  if (!ad) return { title: "Объявление — Шабашка DNR" };
  const url = `${SITE}/ad/${ad.tg_message_id}/`;
  const image = ad.photo_url || LOGO;
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
    <>
      <Header />
      <main
        style={{ maxWidth: 860, margin: "0 auto", padding: "26px 16px 40px" }}
      >
        <div
          style={{
            color: "#67e8f9",
            fontSize: 12,
            letterSpacing: 3,
            fontWeight: 800,
          }}
        >
          ОБЪЯВЛЕНИЕ #{ad.tg_message_id}
        </div>
        <h1
          style={{
            margin: "8px 0 10px",
            fontSize: "clamp(22px,4vw,32px)",
            fontWeight: 900,
          }}
        >
          {ad.title}
        </h1>
        <div
          style={{
            color: "#8b98ad",
            fontSize: 14,
            display: "flex",
            gap: 14,
            flexWrap: "wrap",
          }}
        >
          <span>📍 {ad.city || "Донецк"}</span>
          <span>🗓 {new Date(ad.created_at).toLocaleString("ru-RU")}</span>
          {ad.forwarded_from && (
            <span style={{ color: "#67e8f9" }}>👤 От: {ad.forwarded_from}</span>
          )}
        </div>
        {photos.length === 0 && (
          <PlaceholderArt category={ad.category} height={340} />
        )}
        {photos.map((src) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            key={src}
            src={src}
            alt={ad.title}
            style={{
              width: "100%",
              maxHeight: 560,
              objectFit: "contain",
              background: "#0c0f15",
              border: "1px solid #1c2436",
              borderRadius: 16,
              margin: "16px 0",
            }}
          />
        ))}
        <p
          style={{
            whiteSpace: "pre-wrap",
            fontSize: 17,
            lineHeight: 1.65,
            color: "#dbe3ef",
          }}
        >
          {ad.description}
        </p>
        {ad.phone && (
          <div
            style={{
              fontSize: 24,
              fontWeight: 900,
              color: "#7cfc9b",
              textShadow: "0 0 18px rgba(124,252,155,.35)",
            }}
          >
            📞 {ad.phone}
          </div>
        )}
        <div
          style={{ display: "flex", gap: 10, marginTop: 18, flexWrap: "wrap" }}
        >
          {ad.post_link && (
            <a
              className="btn"
              href={ad.post_link}
              target="_blank"
              rel="noopener"
              style={btnTg}
            >
              ✈ Открыть в Telegram
            </a>
          )}
          {ad.vk_post_url && (
            <a
              className="btn"
              href={ad.vk_post_url}
              target="_blank"
              rel="noopener"
              style={btnVk}
            >
              💙 Пост в VK
            </a>
          )}
        </div>
        <p style={{ marginTop: 22 }}>
          <Link className="chip" style={chip} href="/">
            ← Все объявления
          </Link>
        </p>
      </main>
      <Footer />
    </>
  );
}
