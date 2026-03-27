"""
diagnostics/verify_story_threading.py — Phase 3 story_id consistency check

This is a lightweight DB diagnostic script intended for manual verification.
It does NOT modify any data.
"""

import os
import sys

# Ensure `src.*` imports work (apps/api is the parent of `src/`).
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.lucidpanda.db.base import DBBase
from src.lucidpanda.core.logger import logger


def main() -> None:
    db = DBBase()
    conn = db.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE story_id IS NOT NULL) AS with_story,
                    COUNT(*) FILTER (WHERE story_id IS NULL) AS missing_story
                FROM intelligence;
                """
            )
            row = cursor.fetchone()
            print("\n=== Story Threading: Overview ===")
            print(
                f"total={row['total']}, with_story={row['with_story']}, missing_story={row['missing_story']}"
            )

            cursor.execute(
                """
                WITH per_story AS (
                    SELECT
                        story_id,
                        SUM(CASE WHEN is_story_lead THEN 1 ELSE 0 END) AS lead_cnt,
                        COUNT(*) AS record_cnt
                    FROM intelligence
                    WHERE story_id IS NOT NULL
                    GROUP BY story_id
                )
                SELECT
                    COUNT(*) FILTER (WHERE lead_cnt = 0) AS story_leads_zero,
                    COUNT(*) FILTER (WHERE lead_cnt <> 1) AS story_leads_not_one,
                    MIN(lead_cnt) AS min_leads,
                    MAX(lead_cnt) AS max_leads
                FROM per_story;
                """
            )
            row = cursor.fetchone()
            print("\n=== Story Threading: Lead cardinality ===")
            print(
                "stories with lead_cnt=0="
                f"{row['story_leads_zero']}, lead_cnt<>1={row['story_leads_not_one']}, "
                f"min_leads={row['min_leads']}, max_leads={row['max_leads']}"
            )

            cursor.execute(
                """
                WITH per_story AS (
                    SELECT
                        story_id,
                        SUM(CASE WHEN is_story_lead THEN 1 ELSE 0 END) AS lead_cnt,
                        COUNT(*) AS record_cnt
                    FROM intelligence
                    WHERE story_id IS NOT NULL
                    GROUP BY story_id
                )
                SELECT story_id, lead_cnt, record_cnt
                FROM per_story
                WHERE lead_cnt <> 1
                ORDER BY lead_cnt DESC, record_cnt DESC
                LIMIT 10;
                """
            )
            samples = cursor.fetchall()
            print("\n=== Story Threading: Top inconsistent samples (up to 10) ===")
            if not samples:
                print("No inconsistent story_id found (lead_cnt should be exactly 1).")
            else:
                for s in samples:
                    print(f"story_id={s['story_id']}, lead_cnt={s['lead_cnt']}, record_cnt={s['record_cnt']}")

                    cursor.execute(
                        """
                        SELECT
                            source_id,
                            status,
                            event_cluster_id,
                            is_cluster_lead,
                            is_story_lead,
                            story_id
                        FROM intelligence
                        WHERE story_id = %s
                        ORDER BY is_story_lead DESC, timestamp DESC
                        LIMIT 10;
                        """,
                        (s["story_id"],),
                    )
                    detail_rows = cursor.fetchall()
                    for d in detail_rows:
                        print(
                            f"  - source_id={d['source_id']}, status={d['status']}, "
                            f"event_cluster_id={d['event_cluster_id']}, is_cluster_lead={d['is_cluster_lead']}, "
                            f"is_story_lead={d['is_story_lead']}, story_id={d['story_id']}"
                        )

            cursor.execute(
                """
                SELECT
                    COUNT(*) FILTER (
                        WHERE story_id IS NOT NULL
                          AND event_cluster_id IS NOT NULL
                          AND story_id <> event_cluster_id
                    ) AS story_vs_event_cluster_mismatch
                FROM intelligence;
                """
            )
            row = cursor.fetchone()
            print("\n=== Story Threading: story_id vs event_cluster_id ===")
            print(f"mismatch_cnt={row['story_vs_event_cluster_mismatch']}")

    except Exception as e:
        logger.error(f"verify_story_threading failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()

