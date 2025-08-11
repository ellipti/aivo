import { WorldMapHero } from '../components/WorldMapHero';
import Link from 'next/link';
import { HealthBadge } from '../components/HealthBadge';
import { useTranslations } from 'next-intl';

export default function Page() {
  const t = useTranslations();
  return (
    <main className="container mx-auto px-4 py-10 space-y-16">
      <section className="grid md:grid-cols-2 gap-8 items-center">
        <div className="space-y-4">
          <h1 className="text-4xl md:text-5xl font-bold">{t('hero.title')}</h1>
          <p className="text-lg text-muted-foreground">{t('hero.subtitle')}</p>
          <div className="flex flex-col sm:flex-row gap-3 pt-2">
            <Link
              href="/analyze"
              className="inline-flex justify-center items-center rounded-md bg-primary px-4 py-2 text-primary-foreground hover:opacity-90 w-full sm:w-auto"
            >
              {t('cta.analyze')}
            </Link>
            <Link
              href="/dashboard"
              className="inline-flex justify-center items-center rounded-md border px-4 py-2 hover:bg-accent w-full sm:w-auto"
            >
              {t('cta.dashboard')}
            </Link>
          </div>
          <div className="pt-4">
            <HealthBadge />
          </div>
        </div>
        <WorldMapHero />
      </section>
    </main>
  );
}
