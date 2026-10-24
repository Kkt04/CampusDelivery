import { Link } from "react-router-dom";
import { Brand } from "../../components/Layout";
import { LanguageToggle, useLanguage } from "../../i18n/LanguageContext";

export function LandingPage() {
  const { t } = useLanguage();

  return (
    <div className="h-[100dvh] max-h-[100dvh] flex flex-col justify-between overflow-y-auto sm:overflow-hidden bg-gradient-to-br from-[#C62828] via-[#E53935] to-[#8E1B1B] text-white">
      {/* Top Navigation Bar */}
      <header className="border-b border-white/15 bg-black/10 px-4 sm:px-8 py-3 backdrop-blur-xs flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-white p-1.5 shadow-sm">
            <Brand />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <LanguageToggle light />
          <Link
            to="/login"
            className="rounded-xl bg-white px-5 py-2.5 text-xs sm:text-sm font-bold text-brand hover:bg-red-50 transition-all shadow-sm active:scale-95"
          >
            {t("authSignInBtn")}
          </Link>
        </div>
      </header>

      {/* Main Hero Content - Big, bold, well-distributed across available height */}
      <main className="flex-1 flex flex-col justify-center items-center px-4 sm:px-8 py-3 sm:py-6 text-center max-w-5xl mx-auto w-full">
        {/* Eyebrow Label */}
        <div className="inline-flex items-center gap-2 rounded-full border border-white/30 bg-white/15 px-4 py-1.5 text-xs sm:text-sm font-semibold text-white backdrop-blur-xs shadow-2xs mb-2 sm:mb-3">
          <span className="text-base sm:text-lg">📦</span>
          <span>{t("eyebrow")}</span>
        </div>

        {/* Hero Illustration - Grand, crisp, prominent */}
        <div className="my-1 sm:my-2 flex items-center justify-center">
          <img
            src="/delivery-hero.png"
            alt="Campus parcel delivery illustration"
            className="max-h-[28dvh] sm:max-h-[34dvh] md:max-h-[38dvh] lg:max-h-[42dvh] w-auto max-w-full object-contain drop-shadow-2xl transition-transform duration-300 hover:scale-[1.02]"
          />
        </div>

        {/* Main Heading - visually striking and big */}
        <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight text-white font-serif leading-[1.15]">
          {t("landingHeadingLine1")}<br className="hidden sm:inline" />{" "}
          <span className="text-red-100">{t("landingHeadingLine2")}</span>
        </h1>

        {/* Supporting Description */}
        <p className="mx-auto mt-3 sm:mt-4 max-w-3xl text-sm sm:text-base md:text-lg text-white/95 leading-relaxed font-normal">
          {t("landingDescription")}
        </p>

        {/* Call to Action Buttons */}
        <div className="mt-4 sm:mt-6 flex flex-wrap items-center justify-center gap-4">
          <Link
            to="/login"
            className="inline-flex items-center justify-center rounded-xl bg-white px-8 sm:px-9 py-3 sm:py-3.5 text-sm sm:text-base font-bold text-brand shadow-lg hover:bg-red-50 hover:shadow-xl transition-all active:scale-95"
          >
            {t("landingSignInBtn")}
          </Link>
          <Link
            to="/login?mode=signup"
            className="inline-flex items-center justify-center rounded-xl border-2 border-white/60 bg-white/10 backdrop-blur-xs px-7 sm:px-8 py-3 sm:py-3.5 text-sm sm:text-base font-bold text-white hover:bg-white/20 transition-all active:scale-95"
          >
            {t("landingCreateAccountBtn")}
          </Link>
        </div>

        {/* Trust highlights banner - big, clear metrics */}
        <div className="mt-4 sm:mt-6 grid grid-cols-3 gap-3 sm:gap-6 max-w-xl w-full border-t border-white/20 pt-4 sm:pt-6 text-center">
          <div className="rounded-xl bg-white/10 border border-white/15 px-3 py-2 sm:py-3 backdrop-blur-2xs shadow-sm">
            <div className="text-lg sm:text-2xl md:text-3xl font-extrabold text-white font-serif">{t("landingCustodyLogged")}</div>
            <div className="text-xs sm:text-sm text-white/90 mt-0.5 font-medium">{t("landingTrustCustody")}</div>
          </div>
          <div className="rounded-xl bg-white/10 border border-white/15 px-3 py-2 sm:py-3 backdrop-blur-2xs shadow-sm">
            <div className="text-lg sm:text-2xl md:text-3xl font-extrabold text-white font-serif">{t("landingArrivalAlerts")}</div>
            <div className="text-xs sm:text-sm text-white/90 mt-0.5 font-medium">{t("landingTrustAlerts")}</div>
          </div>
          <div className="rounded-xl bg-white/10 border border-white/15 px-3 py-2 sm:py-3 backdrop-blur-2xs shadow-sm">
            <div className="text-lg sm:text-2xl md:text-3xl font-extrabold text-white font-serif">{t("landingOtpHandover")}</div>
            <div className="text-xs sm:text-sm text-white/90 mt-0.5 font-medium">{t("landingTrustHandover")}</div>
          </div>
        </div>
      </main>
    </div>
  );
}
