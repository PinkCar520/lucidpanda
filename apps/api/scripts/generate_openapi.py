#!/usr/bin/env python3
"""
generate_openapi.py
从 FastAPI 应用自动导出 OpenAPI 规范到 docs/api/openapi.json
用法: python -m scripts.generate_openapi
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def generate_openapi():
    try:
        from src.lucidpanda.api.v1.main import app  # adjust if needed
    except ImportError:
        # 尝试从主入口导入
        try:
            from src.lucidpanda.main import app
        except ImportError:
            print("❌ 无法导入 FastAPI app，请检查路径")
            print("   尝试路径: src.lucidpanda.api.v1.main 或 src.lucidpanda.main")
            sys.exit(1)

    output_dir = Path("docs/api")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 生成 OpenAPI JSON
    openapi_schema = app.openapi()
    output_path = output_dir / "openapi.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, ensure_ascii=False, indent=2)

    print(f"✅ OpenAPI schema generated: {output_path}")
    print(f"   Endpoints: {len(openapi_schema.get('paths', {}))}")
    print(f"   Schemas: {len(openapi_schema.get('components', {}).get('schemas', {}))}")

    # 提示下一步
    print("\n📋 下一步:")
    print("   Web类型生成: npx openapi-typescript docs/api/openapi.json -o web/lib/api-types.ts")
    print("   iOS: 参考 openapi.json 手动更新 Data/APIModels.swift")

if __name__ == "__main__":
    generate_openapi()
