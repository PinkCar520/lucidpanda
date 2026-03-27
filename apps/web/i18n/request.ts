import { getRequestConfig } from 'next-intl/server';
import { locales } from './config';

export default getRequestConfig(async ({ requestLocale }) => {
  // This typically corresponds to the `[locale]` segment
  let locale = await requestLocale;

  // Ensure that a valid locale is used
  const isSupportedLocale = (value: string | undefined): value is (typeof locales)[number] =>
    !!value && locales.includes(value as (typeof locales)[number]);

  if (!isSupportedLocale(locale)) {
    locale = 'en';
  }

  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default
  };
});
