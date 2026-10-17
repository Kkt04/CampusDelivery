"""Initial schema: users, storage, packages, history, pickup tokens/records,
notifications, incidents, audit logs and idempotency keys.

Revision ID: 0001
Revises: 
Create Date: 2026-10-17 08:39:22.503527
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('storage_locations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=False),
    sa.Column('description', sa.String(length=200), nullable=True),
    sa.Column('capacity', sa.Integer(), nullable=False),
    sa.Column('occupied_count', sa.Integer(), nullable=False),
    sa.Column('max_package_size', sa.Enum('SMALL', 'MEDIUM', 'LARGE', name='packagesize', native_enum=False, length=10), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('capacity > 0', name=op.f('ck_storage_locations_capacity_positive')),
    sa.CheckConstraint('occupied_count <= capacity', name=op.f('ck_storage_locations_occupied_within_capacity')),
    sa.CheckConstraint('occupied_count >= 0', name=op.f('ck_storage_locations_occupied_non_negative')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_storage_locations')),
    sa.UniqueConstraint('code', name=op.f('uq_storage_locations_code'))
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('institutional_id', sa.String(length=32), nullable=False),
    sa.Column('full_name', sa.String(length=120), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('role', sa.Enum('LEARNER', 'SECURITY', 'ADMIN', name='role', native_enum=False, length=32), nullable=False),
    sa.Column('password_hash', sa.String(length=100), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)
        batch_op.create_index(batch_op.f('ix_users_institutional_id'), ['institutional_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_users_role'), ['role'], unique=False)

    op.create_table('audit_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('actor_id', sa.Integer(), nullable=True),
    sa.Column('action', sa.String(length=64), nullable=False),
    sa.Column('entity_type', sa.String(length=32), nullable=False),
    sa.Column('entity_id', sa.String(length=64), nullable=True),
    sa.Column('details', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], name=op.f('fk_audit_logs_actor_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs'))
    )
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_audit_logs_action'), ['action'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_actor_id'), ['actor_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_created_at'), ['created_at'], unique=False)
        batch_op.create_index('ix_audit_logs_entity', ['entity_type', 'entity_id'], unique=False)

    op.create_table('idempotency_keys',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('scope', sa.String(length=40), nullable=False),
    sa.Column('key', sa.String(length=80), nullable=False),
    sa.Column('request_hash', sa.String(length=64), nullable=False),
    sa.Column('resource_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_idempotency_keys_user_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_idempotency_keys')),
    sa.UniqueConstraint('user_id', 'scope', 'key', name='uq_idempotency_user_scope_key')
    )
    op.create_table('packages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('internal_code', sa.String(length=24), nullable=False),
    sa.Column('courier_name', sa.String(length=80), nullable=False),
    sa.Column('tracking_id', sa.String(length=64), nullable=True),
    sa.Column('recipient_id', sa.Integer(), nullable=True),
    sa.Column('recipient_hint', sa.String(length=200), nullable=True),
    sa.Column('size', sa.Enum('SMALL', 'MEDIUM', 'LARGE', name='packagesize', native_enum=False, length=10), nullable=False),
    sa.Column('condition', sa.Enum('GOOD', 'DAMAGED', name='packagecondition', native_enum=False, length=16), nullable=False),
    sa.Column('condition_notes', sa.String(length=500), nullable=True),
    sa.Column('status', sa.Enum('RECEIVED', 'VERIFIED', 'STORED', 'READY_FOR_PICKUP', 'PICKUP_REQUESTED', 'COLLECTED', 'UNIDENTIFIED', 'DAMAGED', 'UNDER_INVESTIGATION', 'RETURN_REQUESTED', 'RETURNED', 'LOST', name='packagestatus', native_enum=False, length=32), nullable=False),
    sa.Column('storage_location_id', sa.Integer(), nullable=True),
    sa.Column('arrived_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('received_by_id', sa.Integer(), nullable=False),
    sa.Column('ready_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('notes', sa.String(length=500), nullable=True),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['received_by_id'], ['users.id'], name=op.f('fk_packages_received_by_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], name=op.f('fk_packages_recipient_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['storage_location_id'], ['storage_locations.id'], name=op.f('fk_packages_storage_location_id_storage_locations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_packages')),
    sa.UniqueConstraint('internal_code', name=op.f('uq_packages_internal_code')),
    sa.UniqueConstraint('tracking_id', name=op.f('uq_packages_tracking_id'))
    )
    with op.batch_alter_table('packages', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_packages_arrived_at'), ['arrived_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_packages_recipient_id'), ['recipient_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_packages_status'), ['status'], unique=False)
        batch_op.create_index('ix_packages_status_arrived_at', ['status', 'arrived_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_packages_storage_location_id'), ['storage_location_id'], unique=False)

    op.create_table('incidents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('package_id', sa.Integer(), nullable=True),
    sa.Column('type', sa.Enum('DAMAGE', 'UNIDENTIFIED_RECIPIENT', 'LEARNER_REPORTED_ISSUE', 'MISSING_PACKAGE', 'OPERATIONAL', name='incidenttype', native_enum=False, length=32), nullable=False),
    sa.Column('status', sa.Enum('OPEN', 'RESOLVED', name='incidentstatus', native_enum=False, length=16), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('reported_by_id', sa.Integer(), nullable=False),
    sa.Column('resolved_by_id', sa.Integer(), nullable=True),
    sa.Column('resolution_note', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['package_id'], ['packages.id'], name=op.f('fk_incidents_package_id_packages'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['reported_by_id'], ['users.id'], name=op.f('fk_incidents_reported_by_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['resolved_by_id'], ['users.id'], name=op.f('fk_incidents_resolved_by_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_incidents'))
    )
    with op.batch_alter_table('incidents', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_incidents_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_incidents_package_id'), ['package_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_incidents_status'), ['status'], unique=False)

    op.create_table('notifications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('package_id', sa.Integer(), nullable=True),
    sa.Column('channel', sa.Enum('IN_APP', 'EMAIL', name='notificationchanneltype', native_enum=False, length=16), nullable=False),
    sa.Column('title', sa.String(length=120), nullable=False),
    sa.Column('message', sa.String(length=500), nullable=False),
    sa.Column('delivery_status', sa.Enum('PENDING', 'SENT', 'FAILED', name='notificationstatus', native_enum=False, length=16), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('last_error', sa.String(length=300), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['package_id'], ['packages.id'], name=op.f('fk_notifications_package_id_packages'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_notifications_user_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications'))
    )
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_notifications_delivery_status'), ['delivery_status'], unique=False)
        batch_op.create_index('ix_notifications_user_created', ['user_id', 'created_at'], unique=False)

    op.create_table('package_status_history',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('package_id', sa.Integer(), nullable=False),
    sa.Column('from_status', sa.Enum('RECEIVED', 'VERIFIED', 'STORED', 'READY_FOR_PICKUP', 'PICKUP_REQUESTED', 'COLLECTED', 'UNIDENTIFIED', 'DAMAGED', 'UNDER_INVESTIGATION', 'RETURN_REQUESTED', 'RETURNED', 'LOST', name='packagestatus', native_enum=False, length=32), nullable=True),
    sa.Column('to_status', sa.Enum('RECEIVED', 'VERIFIED', 'STORED', 'READY_FOR_PICKUP', 'PICKUP_REQUESTED', 'COLLECTED', 'UNIDENTIFIED', 'DAMAGED', 'UNDER_INVESTIGATION', 'RETURN_REQUESTED', 'RETURNED', 'LOST', name='packagestatus', native_enum=False, length=32), nullable=False),
    sa.Column('changed_by_id', sa.Integer(), nullable=False),
    sa.Column('reason', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['changed_by_id'], ['users.id'], name=op.f('fk_package_status_history_changed_by_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['package_id'], ['packages.id'], name=op.f('fk_package_status_history_package_id_packages'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_package_status_history'))
    )
    with op.batch_alter_table('package_status_history', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_package_status_history_package_id'), ['package_id'], unique=False)

    op.create_table('pickup_tokens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('package_id', sa.Integer(), nullable=False),
    sa.Column('learner_id', sa.Integer(), nullable=False),
    sa.Column('code_hash', sa.String(length=64), nullable=False),
    sa.Column('salt', sa.String(length=32), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('failed_attempts', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['learner_id'], ['users.id'], name=op.f('fk_pickup_tokens_learner_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['package_id'], ['packages.id'], name=op.f('fk_pickup_tokens_package_id_packages'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_pickup_tokens'))
    )
    with op.batch_alter_table('pickup_tokens', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_pickup_tokens_package_id'), ['package_id'], unique=False)

    op.create_table('pickup_records',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('package_id', sa.Integer(), nullable=False),
    sa.Column('learner_id', sa.Integer(), nullable=False),
    sa.Column('handed_over_by_id', sa.Integer(), nullable=False),
    sa.Column('token_id', sa.Integer(), nullable=False),
    sa.Column('storage_location_code', sa.String(length=20), nullable=True),
    sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['handed_over_by_id'], ['users.id'], name=op.f('fk_pickup_records_handed_over_by_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['learner_id'], ['users.id'], name=op.f('fk_pickup_records_learner_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['package_id'], ['packages.id'], name=op.f('fk_pickup_records_package_id_packages'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['token_id'], ['pickup_tokens.id'], name=op.f('fk_pickup_records_token_id_pickup_tokens'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_pickup_records')),
    sa.UniqueConstraint('package_id', name=op.f('uq_pickup_records_package_id')),
    sa.UniqueConstraint('token_id', name=op.f('uq_pickup_records_token_id'))
    )
    with op.batch_alter_table('pickup_records', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_pickup_records_collected_at'), ['collected_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_pickup_records_learner_id'), ['learner_id'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('pickup_records', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_pickup_records_learner_id'))
        batch_op.drop_index(batch_op.f('ix_pickup_records_collected_at'))

    op.drop_table('pickup_records')
    with op.batch_alter_table('pickup_tokens', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_pickup_tokens_package_id'))

    op.drop_table('pickup_tokens')
    with op.batch_alter_table('package_status_history', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_package_status_history_package_id'))

    op.drop_table('package_status_history')
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.drop_index('ix_notifications_user_created')
        batch_op.drop_index(batch_op.f('ix_notifications_delivery_status'))

    op.drop_table('notifications')
    with op.batch_alter_table('incidents', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_incidents_status'))
        batch_op.drop_index(batch_op.f('ix_incidents_package_id'))
        batch_op.drop_index(batch_op.f('ix_incidents_created_at'))

    op.drop_table('incidents')
    with op.batch_alter_table('packages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_packages_storage_location_id'))
        batch_op.drop_index('ix_packages_status_arrived_at')
        batch_op.drop_index(batch_op.f('ix_packages_status'))
        batch_op.drop_index(batch_op.f('ix_packages_recipient_id'))
        batch_op.drop_index(batch_op.f('ix_packages_arrived_at'))

    op.drop_table('packages')
    op.drop_table('idempotency_keys')
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.drop_index('ix_audit_logs_entity')
        batch_op.drop_index(batch_op.f('ix_audit_logs_created_at'))
        batch_op.drop_index(batch_op.f('ix_audit_logs_actor_id'))
        batch_op.drop_index(batch_op.f('ix_audit_logs_action'))

    op.drop_table('audit_logs')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_role'))
        batch_op.drop_index(batch_op.f('ix_users_institutional_id'))
        batch_op.drop_index(batch_op.f('ix_users_email'))

    op.drop_table('users')
    op.drop_table('storage_locations')
