import { getAllAds, getAdsCount } from "@/lib/api";
import { getTgMembers, getVkMembers, getMaxMembers } from "@/lib/stats";
import { PER_PAGE } from "@/lib/site";
import { FeedPage } from "@/components/ui";

export default async function Home() {
  const [ads, total, tg, vk, max] = await Promise.all([
    getAllAds(1000),
    getAdsCount(),
    getTgMembers(),
    getVkMembers(),
    getMaxMembers(),
  ]);
  const realTotal = total || ads.length;
  const pages = Math.min(50, Math.max(1, Math.ceil(realTotal / PER_PAGE)));
  return (
    <FeedPage
      ads={ads.slice(0, PER_PAGE)}
      current={1}
      pages={pages}
      total={realTotal}
      stats={{ tg, vk, max }}
    />
  );
}
