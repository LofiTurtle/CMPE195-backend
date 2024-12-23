"""Initial migration

Revision ID: 2b058ce426ae
Revises: 
Create Date: 2024-11-12 14:41:12.653094

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2b058ce426ae'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('igbd_game',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('cover', sa.String(length=100), nullable=True),
    sa.Column('artwork', sa.String(length=100), nullable=True),
    sa.Column('summary', sa.String(length=1000), nullable=True),
    sa.Column('first_release_date', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('invalidated_token',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('token_id', sa.String(length=36), nullable=False),
    sa.Column('expired_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('invalidated_token', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_invalidated_token_token_id'), ['token_id'], unique=False)

    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=64), nullable=False),
    sa.Column('password_hash', sa.String(length=128), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )
    op.create_table('community',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=True),
    sa.Column('igbd_id', sa.Integer(), nullable=False),
    sa.Column('owner_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['igbd_id'], ['igbd_game.id'], ),
    sa.ForeignKeyConstraint(['owner_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('connected_account',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=128), nullable=False),
    sa.Column('discord_user_id', sa.String(length=128), nullable=True),
    sa.Column('profile_picture', sa.String(), nullable=True),
    sa.Column('provider', sa.Enum('DISCORD', 'STEAM', name='connectedservice'), nullable=False),
    sa.Column('access_token', sa.Text(), nullable=True),
    sa.Column('refresh_token', sa.Text(), nullable=True),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user_following',
    sa.Column('follower_id', sa.Integer(), nullable=True),
    sa.Column('followed_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['followed_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['follower_id'], ['user.id'], )
    )
    op.create_table('user_profile',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('bio', sa.String(length=1024), nullable=False),
    sa.Column('profile_picture_id', sa.String(length=36), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('post',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=100), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('image_id', sa.String(length=36), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('community_id', sa.Integer(), nullable=False),
    sa.Column('author_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['author_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['community_id'], ['community.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user_communities',
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('community_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['community_id'], ['community.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], )
    )
    op.create_table('comment',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('author_id', sa.Integer(), nullable=True),
    sa.Column('post_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['author_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['post_id'], ['post.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('post_likes',
    sa.Column('post_id', sa.Integer(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['post_id'], ['post.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], )
    )
    op.create_table('comment_likes',
    sa.Column('comment_id', sa.Integer(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['comment_id'], ['comment.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], )
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('comment_likes')
    op.drop_table('post_likes')
    op.drop_table('comment')
    op.drop_table('user_communities')
    op.drop_table('post')
    op.drop_table('user_profile')
    op.drop_table('user_following')
    op.drop_table('connected_account')
    op.drop_table('community')
    op.drop_table('user')
    with op.batch_alter_table('invalidated_token', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_invalidated_token_token_id'))

    op.drop_table('invalidated_token')
    op.drop_table('igbd_game')
    # ### end Alembic commands ###
