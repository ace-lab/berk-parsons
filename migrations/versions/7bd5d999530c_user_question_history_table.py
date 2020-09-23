"""user_question_history_table

Revision ID: 7bd5d999530c
Revises: dffc7dfb2eef
Create Date: 2020-01-28 15:00:44.099298

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7bd5d999530c'
down_revision = 'dffc7dfb2eef'
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_question_history',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user', sa.String(length=100), nullable=True),
    sa.Column('question_name', sa.String(length=64), nullable=True),
    sa.Column('status', sa.Integer(), nullable=True),
    sa.Column('ts', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_question_history_question_name'), 'user_question_history', ['question_name'], unique=False)
    op.create_index(op.f('ix_user_question_history_ts'), 'user_question_history', ['ts'], unique=False)
    op.create_index(op.f('ix_user_question_history_user'), 'user_question_history', ['user'], unique=False)
    # ### end Alembic commands ###


def downgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_user_question_history_user'), table_name='user_question_history')
    op.drop_index(op.f('ix_user_question_history_ts'), table_name='user_question_history')
    op.drop_index(op.f('ix_user_question_history_question_name'), table_name='user_question_history')
    op.drop_table('user_question_history')
    # ### end Alembic commands ###
