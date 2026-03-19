/**
 * Simple in-memory rate limiter
 * 
 * This is a lightweight rate limiter that doesn't require external dependencies.
 * For production, consider using Upstash Redis for distributed rate limiting.
 */

interface RateLimitEntry {
    count: number;
    resetTime: number;
}

class InMemoryRateLimiter {
    private store: Map<string, RateLimitEntry> = new Map();
    private cleanupInterval: NodeJS.Timeout;

    constructor(
        private limit: number = 10,
        private windowMs: number = 60 * 1000 // 1 minute
    ) {
        // Cleanup expired entries every minute
        this.cleanupInterval = setInterval(() => this.cleanup(), 60 * 1000);
    }

    async checkLimit(identifier: string): Promise<{ success: boolean; remaining: number; reset: number }> {
        const now = Date.now();
        const entry = this.store.get(identifier);

        // If no entry or window expired, create new entry
        if (!entry || now > entry.resetTime) {
            const resetTime = now + this.windowMs;
            this.store.set(identifier, { count: 1, resetTime });
            return {
                success: true,
                remaining: this.limit - 1,
                reset: resetTime
            };
        }

        // Increment count
        entry.count++;

        // Check if limit exceeded
        if (entry.count > this.limit) {
            return {
                success: false,
                remaining: 0,
                reset: entry.resetTime
            };
        }

        return {
            success: true,
            remaining: this.limit - entry.count,
            reset: entry.resetTime
        };
    }

    private cleanup() {
        const now = Date.now();
        for (const [key, entry] of this.store.entries()) {
            if (now > entry.resetTime) {
                this.store.delete(key);
            }
        }
    }

    getLimit(): number {
        return this.limit;
    }

    destroy() {
        clearInterval(this.cleanupInterval);
        this.store.clear();
    }
}

// Export singleton instances for different endpoints
export const intelligenceRateLimiter = new InMemoryRateLimiter(20, 60 * 1000); // 20 req/min
export const marketRateLimiter = new InMemoryRateLimiter(10, 60 * 1000);      // 10 req/min
export const sseRateLimiter = new InMemoryRateLimiter(5, 60 * 1000);          // 5 req/min

/**
 * Helper function to get client identifier
 */
export function getClientIdentifier(request: Request): string {
    // Try to get real IP from various headers
    const forwarded = request.headers.get('x-forwarded-for');
    const realIp = request.headers.get('x-real-ip');
    const cfConnectingIp = request.headers.get('cf-connecting-ip'); // Cloudflare

    const ip = forwarded?.split(',')[0].trim() || realIp || cfConnectingIp || 'unknown';

    // For development, use a combination of IP and user agent to allow multiple tabs
    if (process.env.NODE_ENV === 'development') {
        const userAgent = request.headers.get('user-agent') || '';
        return `${ip}-${userAgent.slice(0, 50)}`;
    }

    return ip;
}

/**
 * Middleware to apply rate limiting
 */
export async function applyRateLimit(
    request: Request,
    limiter: InMemoryRateLimiter
): Promise<Response | null> {
    const identifier = getClientIdentifier(request);
    const { success, remaining, reset } = await limiter.checkLimit(identifier);

    // Add rate limit headers
    const headers = new Headers({
        'X-RateLimit-Limit': limiter.getLimit().toString(),
        'X-RateLimit-Remaining': remaining.toString(),
        'X-RateLimit-Reset': new Date(reset).toISOString(),
    });

    if (!success) {
        const retryAfter = Math.ceil((reset - Date.now()) / 1000);
        headers.set('Retry-After', retryAfter.toString());

        return new Response(
            JSON.stringify({
                error: 'Too many requests',
                message: `Rate limit exceeded. Please try again in ${retryAfter} seconds.`,
                retryAfter
            }),
            {
                status: 429,
                headers: {
                    ...Object.fromEntries(headers),
                    'Content-Type': 'application/json'
                }
            }
        );
    }

    // Return null to indicate success, caller should add headers to response
    return null;
}
