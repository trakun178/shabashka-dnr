import type { Metadata } from "next";
import { getAllAds, getAdsCount } from "@/lib/api";
import { getTgMembers, getVkMembers, getMaxMembers } from "@/lib/stats";
import { PER_PAGE, SITE } from "@/lib/site";
import { FeedPage } from "@/components/ui";

type Props = { params: Promise<{ n: string }> };

export async function generateStaticParams() {
  const total = await getAdsCount();
  const pages = Math.min(50, Math.max(1, Math.ceil((total || 0) / PER_PAGE)));
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

  const [ads, total, tg, vk, max] = await Promise.all([
    getAllAds(num * PER_PAGE),
    getAdsCount(),
    getTgMembers(),
    getVkMembers(),
    getMaxMembers(),
  ]);

  const realTotal = total || ads.length;
  const pages = Math.min(50, Math.max(1, Math.ceil(realTotal / PER_PAGE)));
  const slice = ads.slice((num - 1) * PER_PAGE, num * PER_PAGE);

  return (
    <FeedPage
      ads={slice}
      current={num}
      pages={pages}
      total={realTotal}
      stats={{ tg, vk, max }}
    />
  );
}
