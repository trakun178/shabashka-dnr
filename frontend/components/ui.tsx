import Link from "next/link";
import type { CSSProperties } from "react";
import {
  LOGO,
  TG_CHANNEL,
  VK_GROUP,
  MAX_CHANNEL,
  CATEGORIES,
} from "@/lib/site";

// ─────────── заглушки по категориям + форматтер чисел ───────────
const CAT_ART: Record<
  string,
  { emoji: string; glow: string; line: string; text: string }
> = {
  ремонт: {
    emoji: "🛠️",
    glow: "rgba(0,229,255,.28)",
    line: "rgba(0,229,255,.35)",
    text: "#67e8f9",
  },
  сантехника: {
    emoji: "🚿",
    glow: "rgba(74,163,255,.28)",
    line: "rgba(74,163,255,.35)",
    text: "#9ecbff",
  },
  электрика: {
    emoji: "⚡",
    glow: "rgba(255,214,10,.25)",
    line: "rgba(255,214,10,.35)",
    text: "#ffe066",
  },
  строительство: {
    emoji: "🧱",
    glow: "rgba(255,138,61,.25)",
    line: "rgba(255,138,61,.35)",
    text: "#ffb38a",
  },
  грузчики: {
    emoji: "📦",
    glow: "rgba(167,139,250,.25)",
    line: "rgba(167,139,250,.35)",
    text: "#c4b5fd",
  },
  уборка: {
    emoji: "🧹",
    glow: "rgba(124,252,155,.22)",
    line: "rgba(124,252,155,.32)",
    text: "#7cfc9b",
  },
  окна: {
    emoji: "🪟",
    glow: "rgba(103,232,249,.25)",
    line: "rgba(103,232,249,.35)",
    text: "#67e8f9",
  },
  другое: {
    emoji: "🧰",
    glow: "rgba(255,45,120,.25)",
    line: "rgba(255,45,120,.35)",
    text: "#ff8ab5",
  },
};

export function PlaceholderArt({
  category,
  height = 230,
}: {
  category?: string;
  height?: number;
}) {
  const key = category && CAT_ART[category] ? category : "другое";
  const art = CAT_ART[key];
  return (
    <div
      style={{
        height,
        borderRadius: 10,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 10,
        background: `radial-gradient(120% 130% at 15% 0%, ${art.glow} 0%, transparent 55%), linear-gradient(135deg, #101722 0%, #0b0e14 100%)`,
        border: `1px solid ${art.line}`,
      }}
    >
      <div
        style={{
          fontSize: 58,
          lineHeight: 1,
          filter: `drop-shadow(0 0 18px ${art.glow})`,
        }}
      >
        {art.emoji}
      </div>
      <div
        style={{
          color: art.text,
          fontSize: 11,
          letterSpacing: 3,
          fontWeight: 800,
          textTransform: "uppercase",
        }}
      >
        {key}
      </div>
    </div>
  );
}

export function fmt(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n >= 1000) return `${(n / 1000).toFixed(1).replace(".0", "")}K`;
  return String(n);
}
// ────────────────────────────────────────────────────────────────

const btnBase: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  borderRadius: 999,
  padding: "7px 14px",
  fontSize: 13,
  fontWeight: 700,
  textDecoration: "none",
  border: "1px solid transparent",
  whiteSpace: "nowrap",
};
export const btnTg: CSSProperties = {
  ...btnBase,
  background:
    "linear-gradient(90deg, rgba(0,229,255,.16), rgba(0,229,255,.04))",
  borderColor: "rgba(0,229,255,.45)",
  color: "#67e8f9",
};
export const btnVk: CSSProperties = {
  ...btnBase,
  background: "rgba(76,117,165,.14)",
  borderColor: "rgba(76,117,165,.5)",
  color: "#9ecbff",
};
export const btnMax: CSSProperties = {
  ...btnBase,
  background: "rgba(255,45,120,.12)",
  borderColor: "rgba(255,45,120,.45)",
  color: "#ff8ab5",
};
export const chip: CSSProperties = {
  borderRadius: 999,
  border: "1px solid #26304a",
  color: "#aeb9cc",
  padding: "4px 12px",
  fontSize: 12,
  textDecoration: "none",
  background: "#10141d",
};
const stat: CSSProperties = {
  border: "1px solid #22304a",
  background: "#10141d",
  borderRadius: 999,
  padding: "6px 14px",
  fontSize: 13,
  color: "#aeb9cc",
};

export function Header() {
  return (
    <header
      style={{
        position: "sticky",
        top: 0,
        zIndex: 40,
        background: "rgba(10,13,18,.85)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid #161d2c",
      }}
    >
      <div
        style={{
          maxWidth: 1080,
          margin: "0 auto",
          padding: "10px 16px",
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={LOGO}
          alt="Шабашка DNR"
          width={42}
          height={42}
          style={{
            borderRadius: "50%",
            boxShadow: "0 0 16px rgba(0,229,255,.4)",
          }}
        />
        <div style={{ flex: 1, minWidth: 0 }}>
          <Link
            href="/"
            style={{
              color: "#fff",
              textDecoration: "none",
              fontWeight: 900,
              fontSize: 16,
            }}
          >
            Шабашка DNR
          </Link>
          <div style={{ color: "#68758c", fontSize: 11 }}>
            Донецк · Макеевка · ДНР
          </div>
        </div>
        <nav style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <Link className="chip" href="/#lenta" style={chip}>
            Лента
          </Link>
          <a
            className="btn"
            href={TG_CHANNEL}
            target="_blank"
            rel="noopener"
            style={btnTg}
          >
            ✈ Telegram
          </a>
        </nav>
      </div>
    </header>
  );
}

export function Hero({
  total,
  stats,
}: {
  total: number;
  stats?: { tg: number | null; vk: number | null; max: number | null };
}) {
  return (
    <section style={{ textAlign: "center", padding: "44px 16px 8px" }}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={LOGO}
        alt="Шабашка DNR"
        style={{
          width: 148,
          height: 148,
          borderRadius: "50%",
          display: "block",
          margin: "0 auto 18px",
          border: "1px solid #22304a",
          boxShadow:
            "0 0 42px rgba(0,229,255,.35), 0 0 110px rgba(255,45,120,.16)",
        }}
      />
      <div
        style={{
          color: "#67e8f9",
          letterSpacing: 5,
          fontSize: 11,
          fontWeight: 800,
        }}
      >
        TELEGRAM-КАНАЛ · БИРЖА РАБОТЫ
      </div>
      <h1
        style={{
          margin: "10px auto 6px",
          maxWidth: 780,
          fontSize: "clamp(26px,5vw,44px)",
          fontWeight: 900,
          lineHeight: 1.12,
          background: "linear-gradient(92deg,#00e5ff 10%,#ff2d78 90%)",
          WebkitBackgroundClip: "text",
          backgroundClip: "text",
          color: "transparent",
        }}
      >
        Шабашка DNR, Донецк, Макеевка
      </h1>
      <p
        style={{
          color: "#8b98ad",
          maxWidth: 640,
          margin: "0 auto",
          fontSize: 15,
          lineHeight: 1.6,
        }}
      >
        Объявления о работе и услугах: ремонт, стройка, сантехника, электрика,
        грузчики. Свежие посты из Telegram-канала — каждый день.
      </p>
      <div
        style={{
          display: "flex",
          gap: 10,
          justifyContent: "center",
          flexWrap: "wrap",
          marginTop: 18,
        }}
      >
        <span style={stat}>📄 {total} постов</span>
        <span style={stat}>👥 {fmt(stats?.tg)} подписчиков</span>
        {stats?.vk != null && <span style={stat}>💙 {fmt(stats.vk)} в VK</span>}
        {stats?.max != null && (
          <span style={stat}>Ⓜ {fmt(stats.max)} в MAX</span>
        )}
        <span style={{ ...stat, color: "#7cfc9b", borderColor: "#1d4a2c" }}>
          <span className="live">●</span> в эфире
        </span>
      </div>
      <div style={{ marginTop: 18 }}>
        <a
          className="btn"
          href={TG_CHANNEL}
          target="_blank"
          rel="noopener"
          style={{ ...btnTg, padding: "10px 24px", fontSize: 14 }}
        >
          ✈ Подписаться в Telegram
        </a>
      </div>
    </section>
  );
}

export function PromoBanner() {
  return (
    <section
      style={{ maxWidth: 1080, margin: "18px auto 0", padding: "0 16px" }}
    >
      <div
        style={{
          border: "1px solid rgba(255,45,120,.4)",
          background:
            "linear-gradient(90deg, rgba(255,45,120,.12), rgba(0,229,255,.08))",
          borderRadius: 18,
          padding: "16px 20px",
          display: "flex",
          gap: 14,
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <div style={{ fontSize: 30 }}>📢</div>
        <div style={{ flex: 1, minWidth: 220 }}>
          <div style={{ color: "#fff", fontWeight: 800, fontSize: 15 }}>
            Разместите свою рекламу здесь!
          </div>
          <div style={{ color: "#9aa7bb", fontSize: 13 }}>
            Ваше объявление увидят тысячи людей. Мастерам — бесплатно, раз в
            день.
          </div>
        </div>
        <a
          className="btn"
          href={TG_CHANNEL}
          target="_blank"
          rel="noopener"
          style={btnMax}
        >
          Разместить
        </a>
      </div>
    </section>
  );
}

export function CategoryChips() {
  return (
    <nav
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 8,
        justifyContent: "center",
        padding: "18px 16px 4px",
        maxWidth: 1080,
        margin: "0 auto",
      }}
    >
      {CATEGORIES.map((c) => (
        <Link key={c} className="chip" href={`/category/${c}/`} style={chip}>
          {c}
        </Link>
      ))}
    </nav>
  );
}

export function AdCard({ ad }: { ad: any }) {
  return (
    <article
      className="card"
      style={{
        background: "#11141b",
        border: "1px solid #1c2436",
        borderRadius: 16,
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Link
        href={`/ad/${ad.tg_message_id}/`}
        style={{ display: "block", background: "#0c0f15", padding: 10 }}
      >
        {ad.photo_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={ad.photo_url}
            alt={ad.title}
            loading="lazy"
            style={{
              width: "100%",
              height: 230,
              objectFit: "contain",
              borderRadius: 10,
            }}
          />
        ) : (
          <PlaceholderArt category={ad.category} />
        )}
      </Link>
      <div
        style={{
          padding: "12px 14px 14px",
          display: "flex",
          flexDirection: "column",
          gap: 8,
          flex: 1,
        }}
      >
        <Link
          href={`/ad/${ad.tg_message_id}/`}
          style={{
            color: "#f2f5fa",
            textDecoration: "none",
            fontWeight: 700,
            fontSize: 15,
            lineHeight: 1.35,
          }}
        >
          {ad.title}
        </Link>
        <div
          style={{
            color: "#8b98ad",
            fontSize: 13,
            display: "flex",
            flexWrap: "wrap",
            gap: 10,
          }}
        >
          <span>📍 {ad.city || "Донецк"}</span>
          {ad.phone && <span>📞 {ad.phone}</span>}
        </div>
        {ad.forwarded_from && (
          <div style={{ color: "#67e8f9", fontSize: 12 }}>
            👤 От: {ad.forwarded_from}
          </div>
        )}
        <div
          style={{
            marginTop: "auto",
            display: "flex",
            gap: 8,
            flexWrap: "wrap",
            alignItems: "center",
          }}
        >
          <span className="chip" style={chip}>
            {ad.category || "другое"}
          </span>
          <span style={{ color: "#5b6880", fontSize: 12 }}>
            {new Date(ad.created_at).toLocaleDateString("ru-RU")}
          </span>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {ad.post_link && (
            <a
              className="btn"
              href={ad.post_link}
              target="_blank"
              rel="noopener"
              style={btnTg}
            >
              ✈ В Telegram
            </a>
          )}
          {ad.vk_post_url && (
            <a
              className="btn"
              href={ad.vk_post_url}
              target="_blank"
              rel="noopener"
              style={btnVk}
            >
              💙 В VK
            </a>
          )}
        </div>
      </div>
    </article>
  );
}

export function Pagination({
  current,
  pages,
}: {
  current: number;
  pages: number;
}) {
  if (pages <= 1) return null;
  const href = (p: number) => (p === 1 ? "/" : `/page/${p}/`);
  const off: CSSProperties = { ...btnVk, opacity: 0.35, pointerEvents: "none" };
  return (
    <nav
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        gap: 14,
        margin: "28px 0 6px",
        flexWrap: "wrap",
      }}
    >
      {current > 1 ? (
        <Link className="btn" href={href(current - 1)} style={btnVk}>
          ← Назад
        </Link>
      ) : (
        <span style={off}>← Назад</span>
      )}
      <span style={{ color: "#8b98ad", fontSize: 13 }}>
        стр. <b style={{ color: "#67e8f9" }}>{current}</b> из {pages}
      </span>
      {current < pages ? (
        <Link className="btn" href={href(current + 1)} style={btnVk}>
          Вперёд →
        </Link>
      ) : (
        <span style={off}>Вперёд →</span>
      )}
    </nav>
  );
}

export function Footer() {
  return (
    <footer
      style={{
        borderTop: "1px solid #161d2c",
        marginTop: 30,
        padding: "30px 16px 42px",
        background: "#0a0c11",
      }}
    >
      <div style={{ maxWidth: 880, margin: "0 auto", textAlign: "center" }}>
        <p
          style={{
            color: "#77839a",
            fontSize: 13.5,
            lineHeight: 1.75,
            margin: 0,
          }}
        >
          <b style={{ color: "#aeb9cc" }}>Шабашка DNR</b> — доска объявлений о
          работе и услугах в Донецке, Макеевке, Горловке и по всей ДНР. Шабашка,
          ремонт и отделка, плитка, сантехник, электрик, строитель, грузчик,
          разнорабочий, уборка, установка заборов и ворот, кровля, сварка,
          сборка мебели. Свежие объявления из Telegram-канала «Шабашка DNR» —
          обновление автоматически каждый день.
        </p>
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            gap: 10,
            marginTop: 18,
            flexWrap: "wrap",
          }}
        >
          <a
            className="btn"
            href={TG_CHANNEL}
            target="_blank"
            rel="noopener"
            style={btnTg}
          >
            ✈ Telegram-канал
          </a>
          <a
            className="btn"
            href={VK_GROUP}
            target="_blank"
            rel="noopener"
            style={btnVk}
          >
            💙 VK-группа
          </a>
          <a
            className="btn"
            href={MAX_CHANNEL}
            target="_blank"
            rel="noopener"
            style={btnMax}
          >
            Ⓜ MAX-канал
          </a>
        </div>
        <div style={{ color: "#43506a", fontSize: 12, marginTop: 20 }}>
          © {new Date().getFullYear()} Шабашка DNR · shabashka.sofoniya.ru
        </div>
      </div>
    </footer>
  );
}

export type FeedStats = {
  tg: number | null;
  vk: number | null;
  max: number | null;
};
export function FeedPage({
  ads,
  current,
  pages,
  total,
  stats,
}: {
  ads: any[];
  current: number;
  pages: number;
  total: number;
  stats?: FeedStats;
}) {
  return (
    <>
      <Header />
      <Hero total={total} stats={stats} />
      <CategoryChips />
      <PromoBanner />
      <main
        id="lenta"
        style={{ maxWidth: 1080, margin: "0 auto", padding: "18px 16px 10px" }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
            gap: 16,
          }}
        >
          {ads.map((ad) => (
            <AdCard key={ad.tg_message_id} ad={ad} />
          ))}
        </div>
        <Pagination current={current} pages={pages} />
      </main>
      <Footer />
    </>
  );
}
