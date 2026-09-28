import { getAllAds } from "@/lib/api";
import { getTgMembers, getVkMembers } from "@/lib/stats";
import { PER_PAGE, MAX_MEMBERS } from "@/lib/site";
import { FeedPage } from "@/components/ui";

export default async function Home() {
  const [ads, tg, vk] = await Promise.all([
    getAllAds(1000),
    getTgMembers(),
    getVkMembers(),
  ]);
  const pages = Math.min(50, Math.max(1, Math.ceil(ads.length / PER_PAGE)));
  return (
    <FeedPage
      ads={ads.slice(0, PER_PAGE)}
      current={1}
      pages={pages}
      total={ads.length}
      stats={{ tg, vk, max: MAX_MEMBERS }}
    />
  );
}
