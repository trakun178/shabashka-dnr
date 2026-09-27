import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: "https://shabashka.sofoniya.ru/",
      changeFrequency: "hourly",
      priority: 1,
    },
  ];
}
