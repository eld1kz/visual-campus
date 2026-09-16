"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { usePreferences } from "./PreferencesProvider";

const NAV = [
  { href: "/", key: "search" },
  { href: "/collecting", key: "loading" },
  { href: "/profile", key: "profile" },
  { href: "/compare", key: "compare" },
  { href: "/unavailable", key: "error" },
  { href: "/guide", key: "guide" },
  { href: "/wardrobe", key: "wardrobe" },
] as const;

const segment = (on: boolean) =>
  `px-[13px] py-1.5 text-[12.5px] rounded-full border-none ${
    on ? "bg-surface-2 text-ink font-medium" : "bg-transparent text-ink-3"
  }`;

export function Header() {
  const { t, lang, setLang, theme, toggleTheme } = usePreferences();
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-30 flex flex-wrap items-center gap-4 bg-bg px-[26px] py-4">
      <Link href="/" className="flex items-center gap-[9px] text-ink hover:no-underline">
        <span className="size-[15px] rounded-full bg-accent" />
        <span className="font-medium tracking-[-0.015em]">{t.brand}</span>
      </Link>

      <nav className="ml-auto flex flex-wrap gap-1">
        {NAV.map((item) => {
          const on = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded-md px-2 py-[5px] text-[12.5px] hover:no-underline ${
                on ? "font-medium text-ink" : "text-ink-3"
              }`}
            >
              {t.nav[item.key]}
            </Link>
          );
        })}
      </nav>

      <div className="flex items-center gap-0.5">
        <button onClick={() => setLang("ru")} className={segment(lang === "ru")}>
          RU
        </button>
        <button onClick={() => setLang("en")} className={segment(lang === "en")}>
          EN
        </button>
        <button
          onClick={toggleTheme}
          className="rounded-full border-none bg-transparent px-3 py-1.5 text-[12.5px] text-ink-3 hover:text-ink"
        >
          {theme === "light" ? t.theme[0] : t.theme[1]}
        </button>
      </div>
    </header>
  );
}
