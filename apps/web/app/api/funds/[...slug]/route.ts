import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest, { params }: { params: Promise<{ slug: string[] }> }) {
    const { slug } = await params;
    const path = slug.join('/');
    const searchParams = request.nextUrl.searchParams.toString();

    // Use API_INTERNAL_URL (docker network) or fallback to localhost for local dev
    const apiUrl = process.env.API_INTERNAL_URL || 'http://localhost:8001';

    const targetUrl = `${apiUrl}/api/funds/${path}${searchParams ? '?' + searchParams : ''}`;
    console.log(`[Proxy] Forwarding to: ${targetUrl}`);

    try {
        const res = await fetch(targetUrl, { cache: 'no-store' });
        if (!res.ok) {
            return NextResponse.json({ error: `Backend error: ${res.status}` }, { status: res.status });
        }
        const data = await res.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error(`[Proxy] Error:`, error);
        return NextResponse.json({ error: 'Failed to fetch from backend' }, { status: 500 });
    }
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ slug: string[] }> }) {
    const { slug } = await params;
    const path = slug.join('/');
    const apiUrl = process.env.API_INTERNAL_URL || 'http://localhost:8001';
    const targetUrl = `${apiUrl}/api/funds/${path}`;

    try {
        const res = await fetch(targetUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: request.body
        });
        const data = await res.json();
        return NextResponse.json(data);
    } catch (error) {
        return NextResponse.json({ error: 'Failed to post to backend' }, { status: 500 });
    }
}
