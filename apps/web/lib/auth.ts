/**
 * API Authentication Middleware
 * 
 * Provides API key authentication for protecting endpoints.
 * In development mode, authentication is optional for easier testing.
 * In production, authentication is required.
 */

import { NextResponse } from 'next/server';

/**
 * Check if API authentication is enabled
 */
export function isAuthEnabled(): boolean {
    // Always require auth in production ONLY if API key is configured
    if (process.env.NODE_ENV === 'production') {
        return !!process.env.API_KEY;
    }

    // In development, check if API_KEY is set
    return !!process.env.API_KEY;
}

/**
 * Validate API key from request headers
 */
export function validateApiKey(request: Request): boolean {
    // If auth is disabled (dev mode without API_KEY), allow all requests
    if (!isAuthEnabled()) {
        return true;
    }

    const apiKey = request.headers.get('x-api-key') || request.headers.get('authorization')?.replace('Bearer ', '');
    const validKey = process.env.API_KEY;

    if (!validKey) {
        console.warn('[Auth] API_KEY not configured but auth is enabled!');
        return false;
    }

    return apiKey === validKey;
}

/**
 * Middleware to require authentication
 * Returns null if authenticated, or an error Response if not
 */
export function requireAuth(request: Request): Response | null {
    if (!validateApiKey(request)) {
        return NextResponse.json(
            {
                error: 'Unauthorized',
                message: 'Valid API key required. Include it in the X-API-Key header.',
                hint: process.env.NODE_ENV === 'development'
                    ? 'Set API_KEY in .env to enable authentication, or leave it unset for open access in development.'
                    : 'Contact the administrator for an API key.'
            },
            {
                status: 401,
                headers: {
                    'WWW-Authenticate': 'Bearer realm="API", charset="UTF-8"'
                }
            }
        );
    }

    return null;
}

/**
 * Optional authentication - logs warning but allows access
 * Useful for gradual migration to authenticated endpoints
 */
export function optionalAuth(request: Request): { authenticated: boolean; warning?: string } {
    const isAuthenticated = validateApiKey(request);

    if (!isAuthenticated && isAuthEnabled()) {
        return {
            authenticated: false,
            warning: 'Unauthenticated access detected. This endpoint will require authentication in the future.'
        };
    }

    return { authenticated: isAuthenticated };
}

/**
 * Generate a secure API key
 * Usage: node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
 */
export function generateApiKey(): string {
    if (typeof window !== 'undefined') {
        throw new Error('generateApiKey should only be called on the server');
    }

    const crypto = require('crypto');
    return crypto.randomBytes(32).toString('hex');
}

/**
 * Rate limit bypass for authenticated requests
 * Authenticated users get higher rate limits
 */
export function getAuthenticatedRateLimit(request: Request): { limit: number; window: number } {
    const isAuthenticated = validateApiKey(request);

    if (isAuthenticated) {
        return {
            limit: 100,  // 100 requests
            window: 60 * 1000  // per minute
        };
    }

    return {
        limit: 10,   // 10 requests
        window: 60 * 1000  // per minute
    };
}
