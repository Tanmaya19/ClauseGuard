"""Initial schema (PLAN.md section 3).

Generated with `alembic revision --autogenerate` against a live PostgreSQL 16
instance, then adjusted in one respect: autogenerate does not drop the native
ENUM types it creates, so the generated downgrade() left contract_status,
segmentation_method, risk_level and finding_severity behind. A
downgrade-then-upgrade cycle then fails with "type already exists". The
explicit DROP TYPE statements at the end of downgrade() fix that, and
tests/test_migrations.py exercises the round trip.

Revision ID: 0001
Revises: nothing — this is the baseline
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('rubric_versions',
    sa.Column('version', sa.String(length=32), nullable=False),
    sa.Column('yaml_sha256', sa.String(length=64), nullable=False),
    sa.Column('activated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('version', name=op.f('pk_rubric_versions'))
    )
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('email', sa.String(length=320), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_table('contracts',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('filename', sa.String(length=512), nullable=False),
    sa.Column('mime', sa.String(length=128), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('storage_path', sa.String(length=1024), nullable=False),
    sa.Column('raw_text', sa.Text(), nullable=True),
    sa.Column('status', sa.Enum('uploaded', 'extracting', 'segmenting', 'classifying', 'scoring', 'complete', 'failed', name='contract_status'), nullable=False),
    sa.Column('status_detail', sa.String(length=255), nullable=True),
    sa.Column('error_code', sa.String(length=64), nullable=True),
    sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('size_bytes > 0', name=op.f('ck_contracts_size_positive')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_contracts_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_contracts'))
    )
    op.create_index(op.f('ix_contracts_status'), 'contracts', ['status'], unique=False)
    op.create_index(op.f('ix_contracts_user_id'), 'contracts', ['user_id'], unique=False)
    op.create_table('clauses',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('contract_id', sa.UUID(), nullable=False),
    sa.Column('ordinal', sa.Integer(), nullable=False),
    sa.Column('heading', sa.String(length=512), nullable=True),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('char_start', sa.Integer(), nullable=False),
    sa.Column('char_end', sa.Integer(), nullable=False),
    sa.Column('segmentation_method', sa.Enum('numbering', 'heading', 'paragraph', name='segmentation_method'), nullable=False),
    sa.Column('needs_manual_review', sa.Boolean(), nullable=False),
    sa.CheckConstraint('char_end >= char_start', name=op.f('ck_clauses_span_ordered')),
    sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], name=op.f('fk_clauses_contract_id_contracts'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_clauses')),
    sa.UniqueConstraint('contract_id', 'ordinal', name='uq_clauses_contract_ordinal')
    )
    op.create_index(op.f('ix_clauses_contract_id'), 'clauses', ['contract_id'], unique=False)
    op.create_table('reports',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('contract_id', sa.UUID(), nullable=False),
    sa.Column('rubric_version', sa.String(length=32), nullable=False),
    sa.Column('model_version', sa.String(length=64), nullable=False),
    sa.Column('summary_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], name=op.f('fk_reports_contract_id_contracts'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['rubric_version'], ['rubric_versions.version'], name=op.f('fk_reports_rubric_version_rubric_versions')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_reports')),
    sa.UniqueConstraint('contract_id', name=op.f('uq_reports_contract_id'))
    )
    op.create_table('clause_predictions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('clause_id', sa.UUID(), nullable=False),
    sa.Column('label', sa.String(length=64), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('model_version', sa.String(length=64), nullable=False),
    sa.CheckConstraint('confidence >= 0 AND confidence <= 1', name=op.f('ck_clause_predictions_confidence_is_a_probability')),
    sa.ForeignKeyConstraint(['clause_id'], ['clauses.id'], name=op.f('fk_clause_predictions_clause_id_clauses'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_clause_predictions')),
    sa.UniqueConstraint('clause_id', 'label', 'model_version', name='uq_prediction_unique_label')
    )
    op.create_index(op.f('ix_clause_predictions_clause_id'), 'clause_predictions', ['clause_id'], unique=False)
    op.create_table('clause_risk',
    sa.Column('clause_id', sa.UUID(), nullable=False),
    sa.Column('level', sa.Enum('safe', 'caution', 'high_risk', 'unassessable', name='risk_level'), nullable=False),
    sa.Column('rubric_version', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['clause_id'], ['clauses.id'], name=op.f('fk_clause_risk_clause_id_clauses'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['rubric_version'], ['rubric_versions.version'], name=op.f('fk_clause_risk_rubric_version_rubric_versions')),
    sa.PrimaryKeyConstraint('clause_id', name=op.f('pk_clause_risk'))
    )
    op.create_index(op.f('ix_clause_risk_level'), 'clause_risk', ['level'], unique=False)
    op.create_table('risk_findings',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('clause_id', sa.UUID(), nullable=False),
    sa.Column('rule_id', sa.String(length=64), nullable=False),
    sa.Column('severity', sa.Enum('caution', 'high', name='finding_severity'), nullable=False),
    sa.Column('explanation', sa.Text(), nullable=False),
    sa.Column('rubric_version', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['clause_id'], ['clauses.id'], name=op.f('fk_risk_findings_clause_id_clauses'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['rubric_version'], ['rubric_versions.version'], name=op.f('fk_risk_findings_rubric_version_rubric_versions')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_risk_findings')),
    sa.UniqueConstraint('clause_id', 'rule_id', 'rubric_version', name='uq_finding_unique_rule')
    )
    op.create_index(op.f('ix_risk_findings_clause_id'), 'risk_findings', ['clause_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_risk_findings_clause_id'), table_name='risk_findings')
    op.drop_table('risk_findings')
    op.drop_index(op.f('ix_clause_risk_level'), table_name='clause_risk')
    op.drop_table('clause_risk')
    op.drop_index(op.f('ix_clause_predictions_clause_id'), table_name='clause_predictions')
    op.drop_table('clause_predictions')
    op.drop_table('reports')
    op.drop_index(op.f('ix_clauses_contract_id'), table_name='clauses')
    op.drop_table('clauses')
    op.drop_index(op.f('ix_contracts_user_id'), table_name='contracts')
    op.drop_index(op.f('ix_contracts_status'), table_name='contracts')
    op.drop_table('contracts')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_table('rubric_versions')

    # Autogenerate omits these: dropping a table does not drop the ENUM type
    # the column referenced. Without them the schema cannot be rebuilt.
    for enum_name in (
        "finding_severity",
        "risk_level",
        "segmentation_method",
        "contract_status",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
