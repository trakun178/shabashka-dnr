import type { Metadata } from "next";
import { getAllAds } from "@/lib/api";
import { getTgMembers, getVkMembers } from "@/lib/stats";
import { PER_PAGE, SITE } from "@/lib/site";
import { FeedPage } from "@/components/ui";

type Props = { params: Promise<{ n: string }> };

export async function generateStaticParams() {
  const ads = await getAllAds(1000);
  const pages = Math.min(50, Math.ceil(ads.length / PER_PAGE));
  return Array.from({ length: Math.max(0, pages - 1) }, (_, i) => ({
    n: String(i + 2),
  }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { n } = await params;
  return {
    title: `Объявления — страница ${n}`,
    alternates: { canonical: `${SITE}/page/${n}/` },
  };
}

export default async function PageN({ params }: Props) {
  const { n } = await params;
  const num = Math.max(2, parseInt(n, 10) || 2);
  const [ads, tg, vk] = await Promise.all([
    getAllAds(1000),
    getTgMembers(),
    getVkMembers(),
  ]);
  const pages = Math.min(50, Math.max(1, Math.ceil(ads.length / PER_PAGE)));

  return (
    <FeedPage
      ads={ads.slice((num - 1) * PER_PAGE, num * PER_PAGE)}
      current={num}
      pages={pages}
      total={ads.length}
      stats={{ tg, vk, max: MAX_MEMBERS }}
    />
  );
}
