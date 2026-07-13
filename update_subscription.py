"""
订阅简化：将 4 个套餐（free/basic/pro/enterprise）缩减为 2 个（free/paid）
1. 更新 config.py - PLAN_LIMITS 只保留 free 和 paid
2. 更新 quota_service.py - paid 不限制
3. 更新数据库 - 将 basic/pro/enterprise 租户迁移到 paid
4. 更新前端 - 只显示 2 个套餐卡片
"""
import asyncio
import asyncpg

DB_URL = "postgresql://t2d:t2d-saas-2026@localhost:5432/t2d_saas"

async def main():
    conn = await asyncpg.connect(DB_URL)

    # 1. 将所有 basic/pro/enterprise 租户改为 paid
    result = await conn.execute("""
        UPDATE tenants SET plan = 'paid' WHERE plan IN ('basic', 'pro', 'enterprise')
    """)
    print(f"Updated tenants: {result}")

    # 2. 将所有 basic/pro/enterprise 订阅改为 paid，并设置 unlimited 配额
    result = await conn.execute("""
        UPDATE subscriptions SET plan = 'paid',
            message_quota = 999999,
            tg_account_limit = 999999,
            mapping_limit = 999999
        WHERE plan IN ('basic', 'pro', 'enterprise') AND status = 'active'
    """)
    print(f"Updated subscriptions: {result}")

    # 3. 验证
    rows = await conn.fetch("SELECT id, name, plan FROM tenants WHERE id > 0 ORDER BY id")
    print("\nCurrent tenant plans:")
    for r in rows:
        print(f"  Tenant {r['id']} ({r['name']}): {r['plan']}")

    rows = await conn.fetch("SELECT id, tenant_id, plan, message_quota FROM subscriptions WHERE status = 'active'")
    print("\nActive subscriptions:")
    for r in rows:
        print(f"  Sub {r['id']} (tenant {r['tenant_id']}): plan={r['plan']}, quota={r['message_quota']}")

    await conn.close()
    print("\nDone!")

asyncio.run(main())
