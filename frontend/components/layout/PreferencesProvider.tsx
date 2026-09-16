"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { dictionaries, type Dict, type Lang } from "@/lib/i18n";

export type Theme = "light" | "dark";

type Preferences = {
  lang: Lang;
  theme: Theme;
  t: Dict;
  setLang: (lang: Lang) => void;
  toggleTheme: () => void;
};

const PreferencesContext = createContext<Preferences | null>(null);

export const THEME_KEY = "vc-theme";
const LANG_KEY = "vc-lang";

function readStored<T extends string>(key: string, allowed: readonly T[]): T | null {
  try {
    const value = localStorage.getItem(key);
    return allowed.includes(value as T) ? (value as T) : null;
  } catch {
    return null;
  }
}

function store(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Private mode or blocked storage: the preference just isn't remembered.
  }
}

export function PreferencesProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("ru");
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    // The inline script in layout.tsx already applied the stored theme before paint.
    const storedTheme = readStored<Theme>(THEME_KEY, ["light", "dark"]);
    const storedLang = readStored<Lang>(LANG_KEY, ["ru", "en"]);
    /* eslint-disable react-hooks/set-state-in-effect -- sync with browser-only storage after hydration */
    if (storedTheme) setTheme(storedTheme);
    if (storedLang) setLangState(storedLang);
    /* eslint-enable react-hooks/set-state-in-effect */
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    store(LANG_KEY, next);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((current) => {
      const next = current === "light" ? "dark" : "light";
      store(THEME_KEY, next);
      return next;
    });
  }, []);

  return (
    <PreferencesContext.Provider value={{ lang, theme, t: dictionaries[lang], setLang, toggleTheme }}>
      {children}
    </PreferencesContext.Provider>
  );
}

export function usePreferences(): Preferences {
  const value = useContext(PreferencesContext);
  if (!value) throw new Error("usePreferences must be used inside PreferencesProvider");
  return value;
}
