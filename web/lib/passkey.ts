import { startRegistration, startAuthentication } from '@simplewebauthn/browser';
import { authenticatedFetch } from './api-client';
import { Session } from 'next-auth';

/**
 * Register a new Passkey
 */
export async function registerPasskey(session: Session | null, name: string = "My Device") {
  // 1. Get registration options from server
  const optionsRes = await authenticatedFetch('/api/v1/auth/passkeys/register/options', session, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!optionsRes.ok) {
    throw new Error('Failed to get registration options');
  }

  const options = await optionsRes.json();

  // 2. Start WebAuthn registration
  const regResp = await startRegistration({ optionsJSON: options });

  // 3. Verify registration on server
  const verifyRes = await authenticatedFetch('/api/v1/auth/passkeys/register/verify', session, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      registration_data: regResp,
      name: name,
    }),
  });

  if (!verifyRes.ok) {
    const error = await verifyRes.json();
    throw new Error(error.detail || 'Failed to verify registration');
  }

  return await verifyRes.json();
}

/**
 * Prepare for Passkey Authentication (Browser part only)
 * Returns the authentication response and state for server-side verification
 */
export async function authenticatePasskey() {
  // 1. Get authentication options from server
  const optionsRes = await fetch('/api/v1/auth/passkeys/login/options', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!optionsRes.ok) {
    throw new Error('Failed to get authentication options');
  }

  const { state, ...options } = await optionsRes.json();

  // 2. Start WebAuthn authentication
  const authResp = await startAuthentication({ optionsJSON: options });

  return {
    auth_data: authResp,
    state: state,
  };
}
