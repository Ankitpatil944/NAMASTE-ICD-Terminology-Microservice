"""Initial database schema

Revision ID: 0001
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create concepts table
    op.create_table('concepts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('system', sa.String(length=100), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('display', sa.String(length=500), nullable=False),
        sa.Column('definition', sa.Text(), nullable=True),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.Column('source', sa.String(length=200), nullable=True),
        sa.Column('version', sa.String(length=50), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_concepts_id'), 'concepts', ['id'], unique=False)
    op.create_index(op.f('ix_concepts_system'), 'concepts', ['system'], unique=False)
    op.create_index(op.f('ix_concepts_code'), 'concepts', ['code'], unique=False)
    
    # Create mappings table
    op.create_table('mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_system', sa.String(length=100), nullable=False),
        sa.Column('source_code', sa.String(length=100), nullable=False),
        sa.Column('target_system', sa.String(length=100), nullable=False),
        sa.Column('target_code', sa.String(length=100), nullable=False),
        sa.Column('equivalence', sa.String(length=20), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('method', sa.String(length=100), nullable=True),
        sa.Column('evidence', sa.JSON(), nullable=True),
        sa.Column('curator', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mappings_id'), 'mappings', ['id'], unique=False)
    op.create_index(op.f('ix_mappings_source_system'), 'mappings', ['source_system'], unique=False)
    op.create_index(op.f('ix_mappings_source_code'), 'mappings', ['source_code'], unique=False)
    op.create_index(op.f('ix_mappings_target_system'), 'mappings', ['target_system'], unique=False)
    op.create_index(op.f('ix_mappings_target_code'), 'mappings', ['target_code'], unique=False)
    
    # Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('actor', sa.String(length=200), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=True),
        sa.Column('resource_id', sa.String(length=200), nullable=True),
        sa.Column('detail', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_actor'), 'audit_logs', ['actor'], unique=False)
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_resource_type'), 'audit_logs', ['resource_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_resource_id'), 'audit_logs', ['resource_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_timestamp'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_resource_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_resource_type'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_actor'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    op.drop_table('audit_logs')
    
    op.drop_index(op.f('ix_mappings_target_code'), table_name='mappings')
    op.drop_index(op.f('ix_mappings_target_system'), table_name='mappings')
    op.drop_index(op.f('ix_mappings_source_code'), table_name='mappings')
    op.drop_index(op.f('ix_mappings_source_system'), table_name='mappings')
    op.drop_index(op.f('ix_mappings_id'), table_name='mappings')
    op.drop_table('mappings')
    
    op.drop_index(op.f('ix_concepts_code'), table_name='concepts')
    op.drop_index(op.f('ix_concepts_system'), table_name='concepts')
    op.drop_index(op.f('ix_concepts_id'), table_name='concepts')
    op.drop_table('concepts')
