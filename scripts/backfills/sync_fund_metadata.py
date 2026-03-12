import json
import requests
import re
from src.alphasignal.core.database import IntelligenceDB
from src.alphasignal.core.logger import logger

try:
    from pypinyin import pinyin, Style
    HAS_PYPINYIN = True
except Exception:
    HAS_PYPINYIN = False

def get_pinyin_shorthand(name):
    """Convert Chinese name to pinyin shorthand (e.g., '招商中证白酒' -> 'ZSZBBJ')"""
    if not HAS_PYPINYIN:
        return ""
    if not name:
        return ""
    # Get the first letter of each pinyin
    letters = pinyin(name, style=Style.FIRST_LETTER)
    return "".join([item[0].upper() for item in letters if item[0].isalnum()])

def sync_all_funds():
    """Fetch all fund codes and basic info from Market Source and sync to DB."""
    logger.info("🚀 Starting full fund metadata sync...")
    if not HAS_PYPINYIN:
        logger.warning("⚠️ pypinyin is not installed, fallback to legacy shorthand from data source.")
    
    # Market fund list interface
    # FORMAT: ["000001","HXCZHH","华夏成长混合","混合型","HUAXIACHENGZHANGHUNHE"]
    url = "http://fund.eastmoney.com/js/fundcode_search.js"
    
    try:
        response = requests.get(url, timeout=30)
        # Extract the JSON-like array from the JS variable
        match = re.search(r'\[\[.*\]\]', response.text)
        if not match:
            logger.error("❌ Failed to parse market fund list.")
            return

        fund_list = json.loads(match.group())
        logger.info(f"📊 Found {len(fund_list)} funds from Market Source.")

        db = IntelligenceDB()
        conn = db.get_connection()
        cursor = conn.cursor()

        # We will sync basics first
        # fund_metadata (fund_code, fund_name, pinyin_shorthand, investment_type)
        
        count = 0
        for fund in fund_list:
            code = fund[0]
            shorthand_legacy = fund[1] # Legacy acronym
            name = fund[2]
            f_type = fund[3]
            
            # Prefer generated pinyin initials, fallback to legacy shorthand when needed.
            pinyin_idx = get_pinyin_shorthand(name) or (shorthand_legacy or "")
            
            cursor.execute("""
                INSERT INTO fund_metadata (fund_code, fund_name, pinyin_shorthand, investment_type)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (fund_code) DO UPDATE SET
                    fund_name = EXCLUDED.fund_name,
                    pinyin_shorthand = EXCLUDED.pinyin_shorthand,
                    investment_type = EXCLUDED.investment_type,
                    last_full_sync = CURRENT_TIMESTAMP
            """, (code, name, pinyin_idx, f_type))
            
            count += 1
            if count % 1000 == 0:
                conn.commit()
                logger.info(f"✅ Synced {count} funds...")

        conn.commit()
        conn.close()
        logger.info(f"✨ Successfully synced total {count} funds to database.")
        
    except Exception as e:
        logger.error(f"❌ Fund sync failed: {e}")

if __name__ == "__main__":
    sync_all_funds()
