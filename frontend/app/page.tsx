import type { Metadata } from "next";
import Link from "next/link";
import { getAds } from "@/lib/api";

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

export const metadata: Metadata = {
  title: "Шабашка DNR — объявления Донецк, Макеевка",
  description:
    "Доска объявлений о работе и услугах в ДНР: ремонт, строительство, сантехника, электрика, грузчики. Свежие объявления из Telegram-канала «Шабашка DNR».",
  alternates: { canonical: `${SITE}/` },
};

const chip: React.CSSProperties = {
  background: "#242424",
  border: "1px solid #333",
  borderRadius: 999,
  padding: "6px 14px",
  fontSize: 14,
  color: "#f9f9f9",
  textDecoration: "none",
};

export default async function HomePage() {
  const ads = await getAds(200);

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: 16 }}>
      <h1 style={{ fontSize: 28, marginBottom: 4 }}>🛠 Шабашка DNR</h1>
      <p style={{ color: "#999", marginTop: 0 }}>
        Объявления о работе и услугах: Донецк, Макеевка, ДНР
      </p>

      <nav
        style={{ display: "flex", flexWrap: "wrap", gap: 8, margin: "16px 0" }}
      >
        {CATEGORIES.map((c) => (
          <Link key={c} href={`/category/${c}/`} style={chip}>
            {c}
          </Link>
        ))}
      </nav>

      {ads.length === 0 && <p>Пока нет объявлений.</p>}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
          gap: 16,
        }}
      >
        {ads.map((ad: any) => (
          <article
            key={ad.tg_message_id}
            style={{
              background: "#1f1f1f",
              borderRadius: 12,
              overflow: "hidden",
            }}
          >
            <Link
              href={`/ad/${ad.tg_message_id}/`}
              style={{ color: "inherit", textDecoration: "none" }}
            >
              {ad.photo_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={ad.photo_url}
                  alt={ad.title}
                  style={{
                    width: "100%",
                    height: 180,
                    objectFit: "cover",
                    display: "block",
                  }}
                />
              ) : (
                <div
                  style={{
                    width: "100%",
                    height: 180,
                    background: "#2a2a2a",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#666",
                  }}
                >
                  без фото
                </div>
              )}
              <div style={{ padding: 12 }}>
                <h2 style={{ fontSize: 16, margin: 0 }}>{ad.title}</h2>
                <p style={{ color: "#999", margin: "6px 0 0", fontSize: 14 }}>
                  📍 {ad.city}
                  {ad.phone ? ` · 📞 ${ad.phone}` : ""}
                </p>
              </div>
            </Link>
          </article>
        ))}
      </div>

      <p style={{ marginTop: 24, color: "#666", fontSize: 14 }}>
        Источник: Telegram-канал «Шабашка DNR» · обновляется автоматически
      </p>
    </main>
  );
}
