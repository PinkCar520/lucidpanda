import { auth } from "@/auth";
import createIntlMiddleware from 'next-intl/middleware';
import { locales } from './i18n/config';
import { NextRequest } from "next/server";

const intlMiddleware = createIntlMiddleware({
  locales,
  defaultLocale: 'en'
});

export default auth((req: NextRequest & { auth: any }) => {
  const { nextUrl } = req;
  // Consider user logged in only if auth exists AND there's no error (like RefreshAccessTokenError)
  const isLoggedIn = !!req.auth && !req.auth.error;
  
  // Check if it's an auth page (login, register, forgot-password, reset-password)
  const isAuthPage = nextUrl.pathname.includes('/login') || nextUrl.pathname.includes('/register') || nextUrl.pathname.includes('/forgot-password') || nextUrl.pathname.includes('/reset-password');
  
  // If user is on an auth page and logged in, redirect to home
  if (isAuthPage) {
    if (isLoggedIn) {
      // Find the locale from the pathname or fallback to default
      const locale = nextUrl.pathname.split('/')[1] || 'en';
      return Response.redirect(new URL(`/${locale}`, nextUrl));
    }
    return intlMiddleware(req);
  }

  // If user is NOT logged in and NOT on an auth page, redirect to login
  if (!isLoggedIn) {
    const locale = nextUrl.pathname.split('/')[1] || 'en';
    // Only redirect if it's not the public root or api/etc (handled by matcher)
    return Response.redirect(new URL(`/${locale}/login`, nextUrl));
  }

  return intlMiddleware(req);
});

export const config = {
  // Match all pathnames except for
  // - … if they start with `/api`, `/_next` or `/_vercel`
  // - … the ones containing a dot (e.g. `favicon.ico`)
  matcher: ['/((?!api|_next|_vercel|.*\\..*).*)']
};