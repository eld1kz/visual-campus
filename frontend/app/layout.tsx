import type { Metadata } from "next";
import { Instrument_Sans, JetBrains_Mono } from "next/font/google";
import { ChatDrawer } from "@/components/chat/ChatDrawer";
import { GuideFab } from "@/components/guide/GuideFab";
import { GuideProvider } from "@/components/guide/GuideProvider";
import { Header } from "@/components/layout/Header";
import { PreferencesProvider } from "@/components/layout/PreferencesProvider";
import { THEME_KEY } from "@/lib/preferences";
import "./globals.css";

const instrumentSans = Instrument_Sans({
  variable: "--font-instrument-sans",
  subsets: ["latin", "latin-ext"],
  weight: ["400", "500", "600"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Visual Campus",
  description: "Проверенный визуальный профиль кампуса за 30 секунд",
};

// Applies the saved theme before first paint (see Next docs: preventing flash before hydration).
const themeScript = `(function(){try{var t=localStorage.getItem("${THEME_KEY}");if(t==="dark"||t==="light")document.documentElement.setAttribute("data-theme",t)}catch(e){}})()`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ru"
      data-theme="light"
      suppressHydrationWarning
      className={`${instrumentSans.variable} ${jetbrainsMono.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-screen bg-bg text-ink">
        <PreferencesProvider>
          <GuideProvider>
            <Header />
            {children}
            <GuideFab />
            <ChatDrawer />
          </GuideProvider>
        </PreferencesProvider>
      </body>
    </html>
  );
}
