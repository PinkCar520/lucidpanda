import sys
import os
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime
import json

# Add project path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.alphasignal.config import settings
from src.alphasignal.core.logger import logger

def diagnose():
    conn = psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        dbname=settings.POSTGRES_DB
    )
    cursor = conn.cursor(cursor_factory=DictCursor)

    # Specific Target Dates
    targets = [
        {"desc": "宣告与启动 (2025 Apr)", "start": "2025-04-01", "end": "2025-04-10"},
        {"desc": "全面落地 / 关税之夜 (2025 Aug)", "start": "2025-08-01", "end": "2025-08-10"},
        {"desc": "美联储风暴与冲突 (2026 Jan 9-15)", "start": "2026-01-09", "end": "2026-01-15"},
        {"desc": "欧洲与加韩关税打击 (2026 Jan 17-27)", "start": "2026-01-17", "end": "2026-01-27"},
        {"desc": "中东舰队与政府停摆 (2026 Jan 28-31)", "start": "2026-01-28", "end": "2026-02-01"}
    ]

    print("\n" + "="*80)
    print("      AlphaSignal 深度压力测试诊断报告 (Deep Diagnostic Report)      ")
    print("="*80 + "\n")

    for target in targets:
        print(f"📍 核心阶段: {target['desc']}")
        print(f"📅 时间范围: {target['start']} 至 {target['end']}")
        
        # Query intelligence records for this range
        query = """
            SELECT 
                i.*,
                (SELECT value FROM market_indicators WHERE indicator_name = 'FED_REGIME' AND timestamp <= i.timestamp ORDER BY timestamp DESC LIMIT 1) as fed_regime,
                (SELECT percentile FROM market_indicators WHERE indicator_name = 'COT_GOLD_NET' AND timestamp <= i.timestamp ORDER BY timestamp DESC LIMIT 1) as cot_pct
            FROM intelligence i
            WHERE timestamp BETWEEN %s AND %s
            AND urgency_score >= 4
            ORDER BY clustering_score DESC, urgency_score DESC
            LIMIT 3
        """
        cursor.execute(query, (target['start'], target['end']))
        rows = cursor.fetchall()

        if not rows:
            print("  ⚠️  未发现匹配的高优先级情报记录。")
            print("-" * 40)
            continue

        for i, row in enumerate(rows):
            # Format Analysis Result
            summary = row['summary'].get('zh', row['summary']) if isinstance(row['summary'], dict) else row['summary']
            advice = row['actionable_advice'].get('zh', row['actionable_advice']) if isinstance(row['actionable_advice'], dict) else row['actionable_advice']
            
            # Outcome Calculation
            change_1h = ((row['price_1h'] - row['gold_price_snapshot']) / row['gold_price_snapshot'] * 100) if row['price_1h'] and row['gold_price_snapshot'] else 0
            change_24h = ((row['price_24h'] - row['gold_price_snapshot']) / row['gold_price_snapshot'] * 100) if row['price_24h'] and row['gold_price_snapshot'] else 0
            
            fed_status = "Dovish (降息)" if (row['fed_regime'] or 0) > 0 else "Hawkish (加息)" if (row['fed_regime'] or 0) < 0 else "Neutral"
            
            print(f"\n  [{i+1}] 情报标题: {row['content'][:80]}...")
            print(f"      🔹 维度 A (密度/枯竭): Clustering={row['clustering_score']}, Exhaustion={row['exhaustion_score']:.1f}")
            print(f"      🔹 维度 B (筹码拥挤): COT Percentile={row['cot_pct']}% ({'OVERCROWDED' if (row['cot_pct'] or 0) > 85 else 'CLEARING'})")
            print(f"      🔹 维度 C (波动率): GVZ Snapshot={row['gvz_snapshot']:.1f}")
            print(f"      🔹 维度 D (宏观基调): Fed Regime={fed_status} | Adjusted Sentiment={row['sentiment_score']:.2f}")
            print(f"      🔹 市场表现 (1h/24h): {change_1h:+.2f}% / {change_24h:+.2f}%")
            print(f"      💡 AI 实战建议: {advice}")

        print("\n" + "-"*40)

    conn.close()

if __name__ == "__main__":
    diagnose()
