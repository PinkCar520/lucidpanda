import { signOut as nextSignOut } from "next-auth/react";

/**
 * Mature State Purge Logic
 * Ensures NO sensitive data is left in the browser after logout.
 */
export async function atomicSignOut(locale: string = 'en') {
  console.log("[Auth] Starting atomic state purge...");

  // 1. Clear Application LocalStorage
  if (typeof window !== "undefined") {
    // We clear EVERYTHING to be safe, as a mature terminal should.
    localStorage.clear();
    sessionStorage.clear();
    console.log("[Auth] LocalStorage and SessionStorage cleared.");
  }

  // 2. Clear Auth.js Utility Cookies
  // Standard signOut only clears the session token. We want to be cleaner.
  if (typeof document !== "undefined") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i];
      const eqPos = cookie.indexOf("=");
      const name = eqPos > -1 ? cookie.substring(0, eqPos).trim() : cookie.trim();
      
      // Target authjs and next-auth cookies
      if (name.includes("authjs") || name.includes("next-auth")) {
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/;`;
      }
    }
    console.log("[Auth] Auth utility cookies purged.");
  }

  // 3. Perform standard signOut to revoke server-side session
  // This also redirects to login
  await nextSignOut({ 
    callbackUrl: `/${locale}/login`,
    redirect: true 
  });
}
