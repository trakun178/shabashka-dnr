import { getAllAds } from "@/lib/api";
import { PER_PAGE } from "@/lib/site";
import { FeedPage } from "@/components/ui";

export default async function Home() {
  const ads = await getAllAds(1000);
  const pages = Math.min(50, Math.max(1, Math.ceil(ads.length / PER_PAGE)));
  return (
    <FeedPage
      ads={ads.slice(0, PER_PAGE)}
      current={1}
      pages={pages}
      total={ads.length}
    />
  );
}
