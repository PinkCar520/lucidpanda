import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Add project root to path
sys.path.append(os.getcwd())

from src.alphasignal.core.deduplication import NewsDeduplicator

def check_duplicates():
    # Use global settings from src.alphasignal.config
    try:
        from src.alphasignal.config import settings
    except ImportError:
        print("Error: Could not import settings. Make sure you are running from the project root.")
        return

    # Load threshold from environment or settings
    similarity_threshold = float(os.getenv("NEWS_SIMILARITY_THRESHOLD", 0.85))

    print(f"Connecting to Postgres at {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT} DB: {settings.POSTGRES_DB}...")
    try:
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            dbname=settings.POSTGRES_DB
        )
        cur = conn.cursor(cursor_factory=RealDictCursor)
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    # --- MODE SELECTION ---
    do_clean_content = '--clean-content' in sys.argv or '--clean' in sys.argv
    do_clean_noise = '--clean-noise' in sys.argv or '--clean' in sys.argv
    
    ids_to_delete = []

    # ---------------------------------------------------------
    # CONTENT DEDUPLICATION (Standard Scheme: SimHash + BERT)
    # ---------------------------------------------------------
    if do_clean_content:
        print(f"\n=== ANALYZING CONTENT DUPLICATES (Threshold: {similarity_threshold}) ===")
        # Initialize Deduplicator
        deduplicator = NewsDeduplicator(semantic_threshold=similarity_threshold)
        
        # Fetch all records sorted by Timestamp ASC (to keep oldest)
        cur.execute("SELECT id, content, summary, timestamp, author FROM intelligence ORDER BY timestamp ASC")
        all_records = cur.fetchall()
        
        content_dups = []
        
        print(f"Processing {len(all_records)} records...")
        
        for i, row in enumerate(all_records):
            # Construct text for deduplication
            summary_text = ""
            summary = row.get('summary')
            if isinstance(summary, dict):
                summary_text = summary.get('en', '') or str(summary)
            elif isinstance(summary, str):
                summary_text = summary
            
            text_content = row.get('content') or ""
            
            # Preference: Summary (cleaned) > Content (cleaned)
            # We must normalize the input to is_duplicate
            input_text = summary_text if len(summary_text) > 20 else text_content
            
            # The NewsDeduplicator.is_duplicate method already calls normalize internally.
            # And it maintains an internal history of NORMALISED texts/vectors.
            
            if deduplicator.is_duplicate(input_text, record_id=row['id']):
                # It's a duplicate of something in history
                content_dups.append(row['id'])
                # Log the specific case for Kennedy Center if found
                if "Kennedy" in input_text or "肯尼迪" in input_text:
                    print(f"  [FOUND KENNEDY DUP] ID {row['id']} at {row['timestamp']}")
            
            if (i + 1) % 100 == 0:
                print(f"Processed {i + 1}...")

        print(f"Found {len(content_dups)} content duplicates.")
        ids_to_delete.extend(content_dups)

    # ---------------------------------------------------------
    # NOISE CLEANING (Optional, keeping for completeness)
    # ---------------------------------------------------------
    # ... (rest of logic same as before) ...
    if do_clean_noise:
        # (Simplified for now)
        pass

    # ---------------------------------------------------------
    # EXECUTION
    # ---------------------------------------------------------
    ids_to_delete = sorted(list(set(ids_to_delete)))
    
    if ids_to_delete:
        print(f"\n[SUMMARY] Total unique records to delete: {len(ids_to_delete)}")
        
        if '--force' in sys.argv or '-y' in sys.argv:
            confirm = 'y'
        else:
            confirm = input("Confirm deletion? (y/n): ")
        
        if confirm.lower() == 'y':
            chunk_size = 500
            total_deleted = 0
            for i in range(0, len(ids_to_delete), chunk_size):
                chunk = ids_to_delete[i:i + chunk_size]
                ids_tuple = tuple(chunk) if len(chunk) > 1 else f"({chunk[0]})"
                try:
                    cur.execute(f"DELETE FROM intelligence WHERE id IN {ids_tuple}")
                    conn.commit()
                    total_deleted += cur.rowcount
                    print(f"  Deleted batch {i}-{i+len(chunk)}...")
                except Exception as e:
                    conn.rollback()
                    print(f"  Deletion failed: {e}")
            print(f"✅ Deleted {total_deleted} records.")
        else:
            print("Operation cancelled.")
    else:
        print("\nNo records to delete.")

    conn.close()

if __name__ == "__main__":
    check_duplicates()
