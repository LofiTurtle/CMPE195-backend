from datetime import timedelta

from flask import current_app
from flask_migrate import upgrade
from sqlalchemy import text

from server import create_app
from server.models.post import *
from server.models.user import *


def reset_database_schema(app=None):
    app = app or current_app
    with app.app_context():
        db.drop_all()
        with db.engine.connect() as conn:
            conn.execute(text('DROP TABLE IF EXISTS alembic_version'))
            conn.commit()
        upgrade()


def create_test_users(app=None):
    app = app or current_app
    with app.app_context():
        # 3 default users
        user1 = User(username='user1', password='password1')
        user2 = User(username='user2', password='password2')
        user3 = User(username='user3', password='password3')

        # Longer bio for user2
        user2.profile.bio = ('This is a default bio. However, it has many words in it so it is longer than the other '
                             'default bios and it may take up more space in the user interface, therefore it is good '
                             'for testing things.')

        # everyone else follows user1
        user1.followers.append(user2)
        user3.following.append(user1)

        db.session.add_all([user1, user2, user3])
        db.session.commit()
        return user1, user2, user3


def create_test_data(app=None):
    app = app or current_app
    with app.app_context():
        # Get 3 default users
        user1, user2, user3 = create_test_users()

        # IGDB information for Stardew Valley and Elden Ring
        game1 = IgdbGame(
            id=17000,
            name='Stardew Valley',
            cover='https://images.igdb.com/igdb/image/upload/t_cover_big/xrpmydnu9rpxvxfjkiu7.jpg',
            artwork='https://images.igdb.com/igdb/image/upload/t_1080p/ar5l8.jpg',
            summary='Stardew Valley is an open-ended country-life RPG! You’ve inherited your grandfather’s old farm plot in Stardew Valley. Armed with hand-me-down tools and a few coins, you set out to begin your new life. Can you learn to live off the land and turn these overgrown fields into a thriving home? It won’t be easy. Ever since Joja Corporation came to town, the old ways of life have all but disappeared. The community center, once the town’s most vibrant hub of activity, now lies in shambles. But the valley seems full of opportunity. With a little dedication, you might just be the one to restore Stardew Valley to greatness!',
            first_release_date=datetime.fromtimestamp(1456444800)
        )
        game2 = IgdbGame(
            id=119133,
            name='Elden Ring',
            cover='https://images.igdb.com/igdb/image/upload/t_cover_big/co4jni.jpg',
            artwork='https://images.igdb.com/igdb/image/upload/t_1080p/ar1481.jpg',
            summary='Elden Ring is an action RPG developed by FromSoftware and published by Bandai Namco Entertainment, released in February 2022. Directed by Hidetaka Miyazaki, with world-building contributions from novelist George R. R. Martin, the game features an expansive open world called the Lands Between. Players assume the role of a customisable character known as the Tarnished, who must explore this world, battle formidable enemies, and seek to restore the Elden Ring to become the Elden Lord.\n\nThe game builds on the challenging gameplay mechanics familiar from the Dark Souls series but introduces a more open-ended structure with vast exploration, dynamic weather, and a day-night cycle. It offers deep lore, complex characters, and an interconnected world filled with secrets, dungeons, and powerful bosses.',
            first_release_date=datetime.fromtimestamp(1645747200)
        )

        # 2 default communities, 1 with all users in it and another empty
        community1 = Community(name='Stardew Valley Test Community', owner=user1, game=game1)
        community2 = Community(name='Elden Ring Test Community', owner=user2, game=game2)

        community1.users.append(user1)
        community1.users.append(user2)
        community1.users.append(user3)

        base_time = datetime.now() - timedelta(days=1)

        post1a = Post(
            title='Post 1a',
            content='This is post 1a',
            community=community1,
            author=user1,
            created_at=base_time + timedelta(hours=0),
            updated_at=base_time + timedelta(hours=0)
        )
        post2a = Post(
            title='Post 2a',
            content='This is post 2a',
            community=community1,
            author=user2,
            created_at=base_time + timedelta(hours=4),
            updated_at=base_time + timedelta(hours=4)
        )
        post2b = Post(
            title='Post 2b',
            content='This is post 2b',
            community=community1,
            author=user2,
            created_at=base_time + timedelta(hours=8),
            updated_at=base_time + timedelta(hours=8)
        )
        post3a = Post(
            title='Post 3a',
            content='This is post 3a',
            community=community1,
            author=user3,
            created_at=base_time + timedelta(hours=12),
            updated_at=base_time + timedelta(hours=12)
        )
        post3b = Post(
            title='Post 3b',
            content='This is post 3b',
            community=community1,
            author=user3,
            created_at=base_time + timedelta(hours=16),
            updated_at=base_time + timedelta(hours=16)
        )
        post3c = Post(
            title='Post 3c',
            content='This is post 3c',
            community=community1,
            author=user3,
            created_at=base_time + timedelta(hours=20),
            updated_at=base_time + timedelta(hours=20)
        )

        # 1 post in Unpopular Community
        unpopular_post = Post(
            title='Unpopular Post',
            content='An unpopular post',
            community=community2,
            author=user1,
            created_at=base_time + timedelta(hours=22),
            updated_at=base_time + timedelta(hours=22)
        )

        # each user likes lower #'d user's posts
        post1a.likes.append(user2)
        post1a.likes.append(user3)
        post2a.likes.append(user3)
        post2b.likes.append(user3)

        # Old but highly liked post
        popular_post = Post(
            title='Old but popular post',
            content='Wow',
            community=community1,
            author=user1,
            created_at=datetime.now() - timedelta(days=5),
            updated_at=datetime.now() - timedelta(days=5)
        )
        popular_post.likes.append(user1)
        popular_post.likes.append(user2)
        popular_post.likes.append(user3)

        comment_group = [
            Comment(id=4, content='Top-level comment 1',
                    created_at=base_time + timedelta(hours=14),
                    updated_at=base_time + timedelta(hours=14),
                    author_id=1, post_id=1),
            Comment(id=5, content='Top-level comment 2',
                    created_at=base_time + timedelta(hours=15),
                    updated_at=base_time + timedelta(hours=15),
                    author_id=1, post_id=1),
            Comment(id=6, content='Reply to comment 1',
                    created_at=base_time + timedelta(hours=16),
                    updated_at=base_time + timedelta(hours=16),
                    author_id=1, parent_id=4, post_id=1),
            Comment(id=7, content='Another reply to comment 1',
                    created_at=base_time + timedelta(hours=17),
                    updated_at=base_time + timedelta(hours=17),
                    author_id=1, parent_id=4, post_id=1),
            Comment(id=8, content='Reply to reply 3',
                    created_at=base_time + timedelta(hours=18),
                    updated_at=base_time + timedelta(hours=18),
                    author_id=1, parent_id=6, post_id=1),
            Comment(id=9, content='Another reply to reply 3',
                    created_at=base_time + timedelta(hours=19),
                    updated_at=base_time + timedelta(hours=19),
                    author_id=1, parent_id=6, post_id=1),
            Comment(id=10, content='Reply to comment 2',
                    created_at=base_time + timedelta(hours=20),
                    updated_at=base_time + timedelta(hours=20),
                    author_id=1, parent_id=5, post_id=1),
            Comment(id=11, content='Reply to reply 7',
                    created_at=base_time + timedelta(hours=21),
                    updated_at=base_time + timedelta(hours=21),
                    author_id=1, parent_id=7, post_id=1),
            Comment(id=12, content='Another reply to reply 7',
                    created_at=base_time + timedelta(hours=22),
                    updated_at=base_time + timedelta(hours=22),
                    author_id=1, parent_id=7, post_id=1)
        ]

        # add and commit everything
        db.session.add(community1)
        db.session.add(community2)

        db.session.add_all([
            post1a,
            post2a,
            post2b,
            post3a,
            post3b,
            post3c,
            unpopular_post,
        ])

        db.session.add_all(comment_group)
        db.session.commit()


if __name__ == '__main__':
    response = input('Are you sure you want to delete and recreate the database with test data? y/n ')
    if response != 'y' and response != 'Y':
        print('Aborting...')
        exit()

    app = create_app()

    print('Deleting and recreating the database...')
    reset_database_schema(app)

    print('Inserting test data...')
    create_test_data(app)

    print(f'Database initialized with test data.')
