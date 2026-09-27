import type { ReactNode } from "react";
import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  metadataBase: new URL("https://shabashka.sofoniya.ru"),
  title: {
    default: "Шабашка DNR — объявления Донецк, Макеевка",
    template: "%s — Шабашка DNR",
  },
  description:
    "Доска объявлений о работе и услугах в Донецке, Макеевке и ДНР. Мастер и заказы из Telegram-канала «Шабашка DNR».",
  openGraph: {
    type: "website",
    locale: "ru_RU",
    siteName: "Шабашка DNR",
    title: "Шабашка DNR — объявления Донецк, Макеевка",
    description:
      "Объявления о работе и услугах в ДНР: ремонт, строительство, сантехника, электрика, грузчики и другое.",
    images: [
      { url: "/images/logo.webp", width: 512, height: 512, alt: "Шабашка DNR" },
    ],
  },
  twitter: { card: "summary_large_image" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <body
        style={{
          margin: 0,
          background: "#141414",
          color: "#f9f9f9",
          fontFamily:
            "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
        }}
      >
        {children}
      </body>
    </html>
  );
}
