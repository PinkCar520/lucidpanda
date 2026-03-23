import asyncio
import os
import sys
from datetime import date
from dotenv import load_dotenv

# 确保能导入 src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载配置
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
ai_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.ai")
load_dotenv(env_path)
load_dotenv(ai_env_path, override=True)

from src.lucidpanda.core.engine import AlphaEngine
from src.lucidpanda.services.factor_service import FactorService
from src.lucidpanda.config import settings

# 强制使用本地数据库入口，绕过可能的代理 DNS 解析 (db -> 198.x.x.x)
settings.POSTGRES_HOST = "127.0.0.1"

async def test_factor_indexing():
    print("🚀 开始因子聚合 (Factor Indexing) 功能测试...")
    
    # 1. 初始化引擎（这会触发 DBBase._init_db()，确保表已创建）
    engine = AlphaEngine()
    factor_service = engine.factor_service
    
    # 2. 清理今日测试数据，确保测试幂等性
    target_id = "ent_fed_powell"
    today = date.today()
    
    try:
        conn = factor_service.get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM entity_metrics WHERE canonical_id = %s AND metric_date = %s", (target_id, today))
        print(f"🧹 已清理今日关于 {target_id} 的历史测试数据。")
    except Exception as e:
        print(f"⚠️ 清理数据失败 (可能表还未创建): {e}")

    # 3. 模拟多次不同得分的注入
    test_cases = [
        {"cid": target_id, "score": 0.8, "urgency": 3},
        {"cid": target_id, "score": 0.4, "urgency": 2},
        {"cid": target_id, "score": -0.6, "urgency": 1},
    ]
    
    print(f"📊 模拟输入 {len(test_cases)} 条情绪数据...")
    
    for case in test_cases:
        await factor_service.update_entity_factor_async(
            case["cid"], 
            case["score"], 
            case["urgency"]
        )
        print(f"  - 注入: score={case['score']}, urgency={case['urgency']}")

    # 4. 验证聚合逻辑
    # 期望: (0.8 + 0.4 - 0.6) / 3 = 0.2
    # 期望: mention_count = 3
    # 期望: urgency_sum = 6
    
    print("\n🧐 从数据库读取聚合结果进行验证...")
    trend = await factor_service.get_entity_trend_async(target_id, days=1)
    
    if trend:
        metric = trend[0]
        print(f"✅ 聚合结果:")
        print(f"  - 实体: {target_id}")
        print(f"  - 平均情绪 (avg_sentiment): {metric['avg_sentiment']:.4f}")
        print(f"  - 提及次数 (mention_count): {metric['mention_count']}")
        print(f"  - 紧迫度总和 (urgency_sum): {metric['urgency_sum']}")
        
        expected_avg = (0.8 + 0.4 - 0.6) / 3
        if abs(metric['avg_sentiment'] - expected_avg) < 0.0001:
            print("\n🌟 验证成功: 因子计算逻辑准确！")
        else:
            print(f"\n⚠️ 验证偏离: 期望平均分 {expected_avg:.4f}, 实际为 {metric['avg_sentiment']:.4f}")
    else:
        print("❌ 未在数据库中找到聚合指标记录。")

if __name__ == "__main__":
    asyncio.run(test_factor_indexing())
