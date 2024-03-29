"""init

Revision ID: 5004204c3de9
Revises: 
Create Date: 2023-06-21 08:02:48.543869

"""
from alembic import op, context
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5004204c3de9'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_request',
    sa.Column('ray_id', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('question', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('ray_id'),
    schema='bot_interaction_stats'
    )
    op.create_table('brain_response_data',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_request_ray_id', sa.String(), nullable=False),
    sa.Column('type', sa.Enum('SQL', 'CHART', 'CLARIFYING_QUESTION', name='brainresponsetype'), nullable=False),
    sa.Column('question', sa.String(), nullable=False),
    sa.Column('answer', sa.String(), nullable=False),
    sa.Column('sql_script', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['user_request_ray_id'], ['bot_interaction_stats.user_request.ray_id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema='bot_interaction_stats'
    )
    op.create_table('request_outcome',
    sa.Column('ray_id', sa.String(), nullable=False),
    sa.Column('successful', sa.Boolean(), nullable=False),
    sa.Column('error', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['ray_id'], ['bot_interaction_stats.user_request.ray_id'], ),
    sa.PrimaryKeyConstraint('ray_id'),
    schema='bot_interaction_stats'
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('request_outcome', schema='bot_interaction_stats')
    op.drop_table('brain_response_data', schema='bot_interaction_stats')
    op.drop_table('user_request', schema='bot_interaction_stats')
    _context = context.get_context()
    if _context.bind and _context.bind.dialect.name == 'postgresql':
        op.execute('DROP TYPE "brainresponsetype"')
    # ### end Alembic commands ###
