import type { Metadata } from "next";
import Link from "next/link";
import { getAdsByCategory } from "@/lib/api";
import { CATEGORIES, SITE } from "@/lib/site";
import { Header, Footer, AdCard, chip } from "@/components/ui";

type Props = { params: Promise<{ category: string }> };

export function generateStaticParams() {
  return CATEGORIES.map((category) => ({ category }));
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
  const ads = await getAdsByCategory(category);
  return (
    <>
      <Header />
      <main
        style={{ maxWidth: 1080, margin: "0 auto", padding: "26px 16px 20px" }}
      >
        <h1 style={{ fontSize: 28, fontWeight: 900 }}>
          Категория: <span style={{ color: "#67e8f9" }}>{category}</span>
        </h1>
        {ads.length === 0 && (
          <p style={{ color: "#8b98ad" }}>В этой категории пока пусто.</p>
        )}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
            gap: 16,
            marginTop: 16,
          }}
        >
          {ads.map((ad) => (
            <AdCard key={ad.tg_message_id} ad={ad} />
          ))}
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
