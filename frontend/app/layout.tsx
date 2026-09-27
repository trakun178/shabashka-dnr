import type { ReactNode } from "react";
import type { Metadata, Viewport } from "next";
import { SITE, LOGO } from "@/lib/site";

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: {
    default: "Шабашка DNR — объявления Донецк, Макеевка",
    template: "%s — Шабашка DNR",
  },
  description:
    "Доска объявлений о работе и услугах в Донецке, Макеевке и ДНР: ремонт, строительство, сантехника, электрика, грузчики. Свежие объявления из Telegram-канала «Шабашка DNR».",
  icons: { icon: LOGO, apple: LOGO },
  openGraph: {
    type: "website",
    locale: "ru_RU",
    siteName: "Шабашка DNR",
    title: "Шабашка DNR — объявления Донецк, Макеевка",
    description: "Объявления о работе и услугах в ДНР. Обновляется ежедневно.",
    images: [{ url: LOGO, width: 512, height: 512, alt: "Шабашка DNR" }],
  },
  twitter: { card: "summary_large_image" },
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <body
        style={{
          margin: 0,
          background: "#0b0e14",
          color: "#f4f6fb",
          fontFamily:
            "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
        }}
      >
        <style>{`
          html{scroll-behavior:smooth}
          ::selection{background:rgba(0,229,255,.25)}
          .card{transition:transform .16s ease, box-shadow .16s ease, border-color .16s ease}
          .card:hover{transform:translateY(-4px);border-color:rgba(0,229,255,.45);box-shadow:0 12px 34px rgba(0,229,255,.12)}
          .btn{transition:filter .15s ease, transform .15s ease}
          .btn:hover{filter:brightness(1.3);transform:translateY(-1px)}
          .chip{transition:border-color .15s, color .15s}
          .chip:hover{border-color:rgba(0,229,255,.6);color:#67e8f9}
          @keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
          .live{animation:pulse 1.6s infinite}
          ::-webkit-scrollbar{width:10px}
          ::-webkit-scrollbar-thumb{background:#1d2637;border-radius:8px}
        `}</style>
        {children}
      </body>
    </html>
  );
}
