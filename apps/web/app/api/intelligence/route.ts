import { NextResponse } from 'next/server';
import { db, Intelligence } from '@/lib/db';
import { intelligenceRateLimiter, applyRateLimit } from '@/lib/rate-limit';
import { requireAuth, optionalAuth } from '@/lib/auth';

export async function GET(request: Request) {
  // Check authentication (required in production, optional in development)
  const authResponse = requireAuth(request);
  if (authResponse) {
    return authResponse;
  }

  // Apply rate limiting (20 req/min)
  const rateLimitResponse = await applyRateLimit(request, intelligenceRateLimiter);
  if (rateLimitResponse) {
    return rateLimitResponse;
  }

  try {
    const { searchParams } = new URL(request.url);
    const sinceId = searchParams.get('since_id');
    const limit = parseInt(searchParams.get('limit') || '100', 10);
    const offset = parseInt(searchParams.get('offset') || '0', 10);

    let query: string;
    let params: (string | number)[];

    const baseConfidenceExpr = `
      (
        35.0
        + 40.0 * LEAST(1.0, GREATEST(0.0, (COALESCE(corroboration_count, 1) - 1)::float / 4.0))
        + 20.0 * LEAST(1.0, GREATEST(0.0, COALESCE(source_credibility_score, 0.5)))
        + 5.0 * (LEAST(10.0, GREATEST(1.0, COALESCE(urgency_score, 5))) / 10.0)
      )
    `;
    const timeDecayExpr = `
      CASE
        WHEN EXTRACT(EPOCH FROM (NOW() - COALESCE(timestamp, NOW()))) / 3600.0 <= 6 THEN 1.00
        WHEN EXTRACT(EPOCH FROM (NOW() - COALESCE(timestamp, NOW()))) / 3600.0 <= 24 THEN 0.94
        WHEN EXTRACT(EPOCH FROM (NOW() - COALESCE(timestamp, NOW()))) / 3600.0 <= 72 THEN 0.86
        WHEN EXTRACT(EPOCH FROM (NOW() - COALESCE(timestamp, NOW()))) / 3600.0 <= 168 THEN 0.76
        ELSE 0.66
      END
    `;
    const confidenceExpr = `
      LEAST(
        100.0,
        GREATEST(
          0.0,
          (${baseConfidenceExpr}) * (${timeDecayExpr})
        )
      ) AS confidence_score
    `;
    const confidenceLevelExpr = `
      CASE
        WHEN ((${baseConfidenceExpr}) * (${timeDecayExpr})) >= 75 THEN 'HIGH'
        WHEN ((${baseConfidenceExpr}) * (${timeDecayExpr})) >= 55 THEN 'MEDIUM'
        ELSE 'LOW'
      END AS confidence_level
    `;

    if (sinceId) {
      // Incremental update: only fetch items newer than since_id
      // Note: Offset is rarely used with since_id but we can support it if needed.
      // For now, we assume since_id implies "give me the newest items" efficiently.
      query = `SELECT *, ${confidenceExpr}, ${confidenceLevelExpr} FROM intelligence WHERE id > $1 ORDER BY timestamp DESC LIMIT $2 OFFSET $3`;
      params = [parseInt(sinceId, 10), limit, offset];
    } else {
      // Standard pagination: fetch items with limit and offset
      query = `SELECT *, ${confidenceExpr}, ${confidenceLevelExpr} FROM intelligence ORDER BY timestamp DESC LIMIT $1 OFFSET $2`;
      params = [limit, offset];
    }

    const res = await db.query(query, params);
    const data = res.rows as Intelligence[];

    // 获取总数（用于分页器）
    let totalCount = 0;
    if (!sinceId) {
      // 只在标准分页时查询总数（增量更新不需要）
      const countRes = await db.query('SELECT COUNT(*) as count FROM intelligence');
      totalCount = parseInt(countRes.rows[0].count, 10);
    }

    return NextResponse.json({
      data,
      latest_id: data.length > 0 ? data[0].id : null,
      count: data.length,
      total: totalCount,
      page: Math.floor(offset / limit) + 1,
      total_pages: totalCount > 0 ? Math.ceil(totalCount / limit) : 0,
      has_more: offset + data.length < totalCount
    });
  } catch (error) {
    console.error('Database error:', error);
    return NextResponse.json({ error: 'Failed to fetch intelligence data' }, { status: 500 });
  }
}
