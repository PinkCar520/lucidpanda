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

import { emitReauth, addToQueue, processQueue, setRefreshing, getIsRefreshing } from '@/lib/auth-events';

interface AuthenticatedFetchOptions extends RequestInit {
  skipReauth?: boolean;
}

export async function authenticatedFetch(
  url: string,
  session: Session | null,
  options?: AuthenticatedFetchOptions
): Promise<Response> {
  const headers = new Headers(options?.headers);

  // Helper to apply current session token to headers
  const applyAuth = (token: string) => {
    headers.set('Authorization', `Bearer ${token}`);
  };

  if (session?.accessToken) {
    applyAuth(session.accessToken);
  }

  const isClient = typeof window !== 'undefined';
  const fullUrl = url.startsWith('http') ? url : (isClient ? url : `${API_INTERNAL_URL}${url}`);

  if (isClient) startProgress();

  try {
    const response = await fetch(fullUrl, {
      ...options,
      headers,
    });

    // Handle 401 Unauthorized - The core of Soft Expiry
    if (response.status === 401 && isClient && !options?.skipReauth) {
      console.warn(`[api-client] 401 detected for ${url}. Attempting recovery...`);

      // 1. If we are already refreshing, just queue this request
      if (getIsRefreshing()) {
        return new Promise((resolve) => {
          addToQueue((newToken: string) => {
            applyAuth(newToken);
            resolve(fetch(fullUrl, { ...options, headers }));
          });
        });
      }

      setRefreshing(true);

      // 2. Try to silently refresh via NextAuth first
      const { getSession } = await import('next-auth/react');
      const newSession = await getSession();

      if (newSession?.accessToken) {
        console.log('[api-client] Silent refresh successful.');
        processQueue(newSession.accessToken);
        applyAuth(newSession.accessToken);
        return fetch(fullUrl, { ...options, headers });
      }

      // 3. Silent refresh failed, trigger the UI Modal
      return new Promise((resolve, reject) => {
        emitReauth((newToken: string) => {
          console.log('[api-client] Re-auth successful, retrying original request.');
          applyAuth(newToken);
          fetch(fullUrl, { ...options, headers }).then(resolve).catch(reject);
        });
      });
    }

    return response;
  } finally {
    if (isClient) stopProgress();
  }
}