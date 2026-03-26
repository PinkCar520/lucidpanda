import logging
import os
import sys
import time

import akshare as ak

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.lucidpanda.core.database import IntelligenceDB

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IndustrySyncer:
    def __init__(self):
        self.db = IntelligenceDB()
        self.conn = self.db.get_connection()

    def sync_l1_industries(self):
        """Fetch and store Shenwan Level 1 Industries."""
        logger.info("📡 Fetching SW Level 1 Industries...")
        try:
            df = ak.sw_index_first_info()
            # Columns: 行业代码 (801010.SI), 行业名称 (农林牧渔)

            count = 0
            with self.conn.cursor() as cursor:
                for _, row in df.iterrows():
                    raw_code = str(row['行业代码'])
                    code = raw_code.split('.')[0] # Remove .SI
                    name = str(row['行业名称'])

                    cursor.execute("""
                        INSERT INTO industry_definitions (industry_code, industry_name, level)
                        VALUES (%s, %s, 1)
                        ON CONFLICT (industry_code) DO UPDATE SET
                            industry_name = EXCLUDED.industry_name
                    """, (code, name))
                    count += 1
            self.conn.commit()
            logger.info(f"✅ Synced {count} Level 1 Industries.")
            return [str(row['行业代码']).split('.')[0] for _, row in df.iterrows()]

        except Exception as e:
            logger.error(f"Failed to sync L1: {e}")
            self.conn.rollback()
            return []

    def sync_l2_industries(self):
        """Fetch and store Shenwan Level 2 Industries."""
        logger.info("📡 Fetching SW Level 2 Industries...")
        try:
            # index_realtime_sw returns ~124 indices (likely L2)
            df = ak.index_realtime_sw()
            # Columns: 指数代码, 指数名称

            codes = []
            with self.conn.cursor() as cursor:
                for _, row in df.iterrows():
                    code = str(row['指数代码'])
                    name = str(row['指数名称'])

                    # Filter: L2 usually starts with 801 but is not in L1 list?
                    # Actually just store them all as L2 for now if they are not in L1 list (checked via DB later)
                    # But for now, we just mark them as level 2.
                    # Note: index_realtime_sw MIGHT contain L1? Previous check said no.

                    cursor.execute("""
                        INSERT INTO industry_definitions (industry_code, industry_name, level)
                        VALUES (%s, %s, 2)
                        ON CONFLICT (industry_code) DO UPDATE SET
                            industry_name = EXCLUDED.industry_name,
                            level = 2
                    """, (code, name))
                    codes.append(code)

            self.conn.commit()
            logger.info(f"✅ Synced {len(codes)} Level 2 Industries.")
            return codes

        except Exception as e:
            logger.error(f"Failed to sync L2: {e}")
            self.conn.rollback()
            return []

    def sync_constituents(self, industry_code, level):
        """Fetch members of an industry and update stock_metadata."""
        try:
            # logger.info(f"   Fetching members for {industry_code} (L{level})...")
            df = ak.index_component_sw(symbol=industry_code)
            if df.empty: return

            # Columns: 序号, 证券代码, 证券名称, ...

            updates = []
            for _, row in df.iterrows():
                stock_code = str(row['证券代码'])
                stock_name = str(row['证券名称'])
                updates.append((stock_code, stock_name))

            if not updates: return

            with self.conn.cursor() as cursor:
                # We need to know industry name to verify? No, code is enough.
                # Get industry name from DB for denormalization
                cursor.execute("SELECT industry_name FROM industry_definitions WHERE industry_code = %s", (industry_code,))
                res = cursor.fetchone()
                industry_name = res[0] if res else ""

                for s_code, s_name in updates:
                    # Determine market
                    market = 'SZ'
                    if s_code.startswith('6') or s_code.startswith('9'): market = 'SH'
                    elif s_code.startswith('8') or s_code.startswith('4'): market = 'BJ'

                    if level == 1:
                        cursor.execute("""
                            INSERT INTO stock_metadata (stock_code, stock_name, industry_l1_code, industry_l1_name, market)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (stock_code) DO UPDATE SET
                                stock_name = EXCLUDED.stock_name,
                                industry_l1_code = EXCLUDED.industry_l1_code,
                                industry_l1_name = EXCLUDED.industry_l1_name,
                                updated_at = CURRENT_TIMESTAMP
                        """, (s_code, s_name, industry_code, industry_name, market))
                    else:
                         cursor.execute("""
                            INSERT INTO stock_metadata (stock_code, stock_name, industry_l2_code, industry_l2_name, market)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (stock_code) DO UPDATE SET
                                stock_name = EXCLUDED.stock_name,
                                industry_l2_code = EXCLUDED.industry_l2_code,
                                industry_l2_name = EXCLUDED.industry_l2_name,
                                updated_at = CURRENT_TIMESTAMP
                        """, (s_code, s_name, industry_code, industry_name, market))

            self.conn.commit()
            # logger.info(f"      -> Updated {len(updates)} stocks.")

        except Exception as e:
            logger.warning(f"Failed members for {industry_code}: {e}")
            self.conn.rollback()

    def run(self):
        logger.info("🚀 Starting Industry Sync...")

        # 1. Sync L1
        l1_codes = self.sync_l1_industries()

        # 2. Sync L1 Constituents
        logger.info(f"🔄 Syncing Constituents for {len(l1_codes)} L1 Industries...")
        for i, code in enumerate(l1_codes):
            self.sync_constituents(code, 1)
            time.sleep(0.3)
            if (i+1) % 5 == 0: logger.info(f"   Progress L1: {i+1}/{len(l1_codes)}")

        # 3. Sync L2
        l2_codes = self.sync_l2_industries()

        # 4. Sync L2 Constituents
        logger.info(f"🔄 Syncing Constituents for {len(l2_codes)} L2 Industries...")
        for i, code in enumerate(l2_codes):
            self.sync_constituents(code, 2)
            time.sleep(0.3)
            if (i+1) % 10 == 0: logger.info(f"   Progress L2: {i+1}/{len(l2_codes)}")

        logger.info("✅ All Done!")
        self.conn.close()

if __name__ == "__main__":
    syncer = IndustrySyncer()
    syncer.run()
