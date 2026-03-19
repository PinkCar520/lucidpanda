export const locales = ['en', 'zh', 'ru'] as const;
export type Locale = (typeof locales)[number];

export const localeNames: Record<Locale, string> = {
    en: 'English',
    zh: '中文',
    ru: 'Русский'
};
