// web/lib/api-client.ts
import { Session } from 'next-auth'; // Session type
import { API_INTERNAL_URL } from '@/lib/constants'; // Backend API URL

interface AuthenticatedFetchOptions extends RequestInit {
  // Custom options can be added here if needed
}

export async function authenticatedFetch(
  url: string,
  session: Session | null,
  options?: AuthenticatedFetchOptions
): Promise<Response> {
  const headers = new Headers(options?.headers);

  if (session?.accessToken) {
    headers.set('Authorization', `Bearer ${session.accessToken}`);
  } else if (session) {
    console.warn('[api-client] Session provided but accessToken is missing. This will likely result in 401.');
  }

  // Determine base URL:
  // - On client-side (browser): use relative URL to allow Next.js proxying and avoid CORS/Internal Hostname issues.
  // - On server-side (SSR): use API_INTERNAL_URL to talk to the backend service directly.
  const isClient = typeof window !== 'undefined';
  const fullUrl = url.startsWith('http') ? url : (isClient ? url : `${API_INTERNAL_URL}${url}`);

  const response = await fetch(fullUrl, {
    ...options,
    headers,
  });

  // NextAuth.js handles 401 for token refresh internally via its callbacks.
  // If a 401 reaches here, it means next-auth couldn't refresh the token,
  // or it's a 401 for a different reason (e.g., completely invalid session).
  // In most cases, next-auth will eventually redirect to the login page
  // if the session is truly invalid.
  // We can add specific client-side logic here if needed, but it's often
  // best to let next-auth handle the primary redirection.
  if (response.status === 401) {
    // Optionally, if this 401 needs to explicitly trigger a client-side signOut
    // if next-auth's internal mechanisms haven't already
    // For many apps, just allowing the component re-render with a null session
    // after next-auth has failed to refresh (and potentially redirecting via middleware)
    // is sufficient.
  }

  return response;
}