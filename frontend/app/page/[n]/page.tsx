import type { Metadata } from "next";
import { getAllAds } from "@/lib/api";
import { getTgMembers, getVkMembers } from "@/lib/stats";
import { PER_PAGE, SITE, MAX_MEMBERS } from "@/lib/site";
import { FeedPage } from "@/components/ui";

type Props = { params: Promise<{ n: string }> };

  const [ads, total, tg, vk, max] = await Promise.all([
    getAllAds(1000), getAdsCount(), getTgMembers(), getVkMembers(), getMaxMembers(),
  ]);
  const realTotal = total || ads.length;
  const pages = Math.min(50, Math.max(1, Math.ceil(realTotal / PER_PAGE)));
  ...
  stats={{ tg, vk, max }}
  total={realTotal}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { n } = await params;
  return {
    title: `Объявления — страница ${n}`,
    alternates: { canonical: `${SITE}/page/${n}/` },
  };
}

  const [ads, total, tg, vk, max] = await Promise.all([
    getAllAds(1000), getAdsCount(), getTgMembers(), getVkMembers(), getMaxMembers(),
  ]);
  const realTotal = total || ads.length;
  const pages = Math.min(50, Math.max(1, Math.ceil(realTotal / PER_PAGE)));
  ...
  stats={{ tg, vk, max }}
  total={realTotal}
