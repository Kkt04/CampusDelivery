import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { en } from "./en";
import { hi } from "./hi";
import type { Language, TranslationDictionary } from "./types";

interface LanguageContextType {
  lang: Language;
  setLang: (lang: Language) => void;
  toggleLang: () => void;
  t: (key: keyof TranslationDictionary) => string;
  toggleLabel: string;
}

const LanguageContext = createContext<LanguageContextType | null>(null);

const STORAGE_KEY = "campus_delivery_lang";

const DICTIONARIES: Record<Language, TranslationDictionary> = { en, hi };

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Language>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved === "en" || saved === "hi") return saved;
    } catch {
      // Ignore localStorage errors
    }
    return "en";
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch {
      // Ignore localStorage errors
    }
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((next: Language) => {
    setLangState(next);
  }, []);

  const toggleLang = useCallback(() => {
    setLangState((prev) => (prev === "en" ? "hi" : "en"));
  }, []);

  const t = useCallback(
    (key: keyof TranslationDictionary): string => {
      const dict = DICTIONARIES[lang] || en;
      return dict[key] ?? en[key] ?? key;
    },
    [lang]
  );

  const toggleLabel = useMemo(() => {
    return lang === "en" ? "English → हिंदी" : "हिंदी → English";
  }, [lang]);

  const value = useMemo(
    () => ({ lang, setLang, toggleLang, t, toggleLabel }),
    [lang, setLang, toggleLang, t, toggleLabel]
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageContextType {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return ctx;
}

export function LanguageToggle({ className = "", light = false }: { className?: string; light?: boolean }) {
  const { toggleLang, toggleLabel, lang } = useLanguage();

  return (
    <button
      type="button"
      onClick={toggleLang}
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold tracking-wide transition-all active:scale-95 ${
        light
          ? "border border-white/30 bg-white/10 text-white hover:bg-white/20 backdrop-blur-xs shadow-2xs"
          : "border border-line bg-surface-alt text-brand hover:border-brand/40 hover:bg-brand-soft/70 shadow-2xs"
      } ${className}`}
      aria-label={`Current language: ${lang === "en" ? "English" : "Hindi"}. Click to toggle language.`}
      title={lang === "en" ? "हिंदी में बदलें" : "Switch to English"}
    >
      <span className="text-sm">🌐</span>
      <span>{toggleLabel}</span>
    </button>
  );
}
