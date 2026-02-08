// web/lib/api-client.ts
import { Session } from 'next-auth'; // Session type
import { API_INTERNAL_URL } from '@/lib/constants'; // Backend API URL
import NProgress from 'nprogress';

// Configure NProgress to be less jittery
if (typeof window !== 'undefined') {
  NProgress.configure({ showSpinner: false, trickleSpeed: 200 });
}

let activeRequests = 0;

function startProgress() {
  if (typeof window !== 'undefined') {
    if (activeRequests === 0) {
      NProgress.start();
    }
    activeRequests++;
  }
}

function stopProgress() {
  if (typeof window !== 'undefined') {
    activeRequests--;
    if (activeRequests <= 0) {
      activeRequests = 0;
      NProgress.done();
    }
  }
}

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

  if (isClient) startProgress();

  try {
    const response = await fetch(fullUrl, {
      ...options,
      headers,
    });

    // Handle 401 Unauthorized
    if (response.status === 401) {
      console.error(`[api-client] Unauthorized request to ${url}. Token might be expired or invalid.`);
      
      // On client-side, if we get a 401, it means the session is likely dead (refresh failed)
      if (isClient) {
        const { signOut } = await import('next-auth/react');
        // Force sign out and redirect to login with a specific error flag
        signOut({ callbackUrl: `/${window.location.pathname.split('/')[1]}/login?error=session_expired` });
      }
    }

    return response;
  } finally {
    if (isClient) stopProgress();
  }
}