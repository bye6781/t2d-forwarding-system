"""Normalize forwarding targets and retire legacy filter configs."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260715_01"
down_revision = "20260715_00"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mapping_targets",
        sa.Column("mapping_id", sa.BigInteger(), nullable=False),
        sa.Column("bot_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["mapping_id"], ["mappings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bot_id"], ["dingtalk_bots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("mapping_id", "bot_id"),
    )
    op.execute(
        """
        INSERT INTO mapping_targets (mapping_id, bot_id)
        SELECT DISTINCT m.id, b.id
        FROM mappings m
        CROSS JOIN LATERAL jsonb_array_elements_text(m.target_bot_ids::jsonb) target(value)
        JOIN dingtalk_bots b ON b.tenant_id = m.tenant_id AND b.bot_id = target.value
        ON CONFLICT DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO filter_rules (tenant_id, name, rule_type, config, description, priority, enabled)
        SELECT tenant_id, '旧版过滤配置', 'legacy_config', config,
               '由 filter_configs 自动迁移', 0, COALESCE((config->>'enabled')::boolean, true)
        FROM filter_configs
        WHERE config <> '{}'::jsonb
        """
    )
    op.drop_table("filter_configs")
    op.drop_column("mappings", "target_bot_ids")


def downgrade() -> None:
    op.add_column(
        "mappings",
        sa.Column(
            "target_bot_ids", postgresql.JSONB(), nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_table(
        "filter_configs",
        sa.Column(
            "tenant_id", sa.BigInteger(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True,
        ),
        sa.Column(
            "config", postgresql.JSONB(), nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.execute(
        """
        UPDATE mappings m SET target_bot_ids = targets.bot_ids
        FROM (
          SELECT mt.mapping_id, jsonb_agg(b.bot_id ORDER BY b.id) AS bot_ids
          FROM mapping_targets mt JOIN dingtalk_bots b ON b.id = mt.bot_id
          GROUP BY mt.mapping_id
        ) targets
        WHERE m.id = targets.mapping_id
        """
    )
    op.execute(
        """
        INSERT INTO filter_configs (tenant_id, config, updated_at)
        SELECT DISTINCT ON (tenant_id) tenant_id, config, updated_at
        FROM filter_rules WHERE rule_type = 'legacy_config'
        ORDER BY tenant_id, priority, id
        """
    )
    op.execute("DELETE FROM filter_rules WHERE rule_type = 'legacy_config'")
    op.drop_table("mapping_targets")
