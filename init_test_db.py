import time
from datetime import timedelta

from server import app, db
from server.models.user import *
from server.models.post import *

def stagger_add(objects: list, delay_s: int = .05):
    for obj in objects:
        db.session.add(obj)
        db.session.commit()
        time.sleep(delay_s)


if __name__ == '__main__':
    response = input('Are you sure you want to delete and recreate the database with test data? y/n ')
    if response != 'y' and response != 'Y':
        print('Aborting...')
        exit()

    with app.app_context():
        db.drop_all()
        db.create_all()

        # 3 default users
        user1 = User(username='user1', password='password1')
        user2 = User(username='user2', password='password2')
        user3 = User(username='user3', password='password3')

        # everyone else follows user1
        user1.followers.append(user2)
        user3.following.append(user1)

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
            cover='https://images.igdb.com/igdb/image/upload/t_thumb/co4jni.jpg',
            artwork='https://images.igdb.com/igdb/image/upload/t_thumb/ar1481.jpg',
            summary='Elden Ring is an action RPG developed by FromSoftware and published by Bandai Namco Entertainment, released in February 2022. Directed by Hidetaka Miyazaki, with world-building contributions from novelist George R. R. Martin, the game features an expansive open world called the Lands Between. Players assume the role of a customisable character known as the Tarnished, who must explore this world, battle formidable enemies, and seek to restore the Elden Ring to become the Elden Lord.\n\nThe game builds on the challenging gameplay mechanics familiar from the Dark Souls series but introduces a more open-ended structure with vast exploration, dynamic weather, and a day-night cycle. It offers deep lore, complex characters, and an interconnected world filled with secrets, dungeons, and powerful bosses.',
            first_release_date=datetime.fromtimestamp(1645747200)
        )

        # 2 default communities, 1 with all users in it and another empty
        community1 = Community(name='Stardew Valley Test Community', owner=user1, game=game1)
        community2 = Community(name='Elden Ring Test Community', owner=user2, game=game2)

        community1.users.append(user1)
        community1.users.append(user2)
        community1.users.append(user3)
        community2.users.append(user1)

        # user 1 has 1 post, user 2 has 2, etc.
        post1a = Post(title='Post 1a', content='This is post 1a', community=community1, author=user1)
        post2a = Post(title='Post 2a', content='This is post 2a', community=community1, author=user2)
        post2b = Post(title='Post 2b', content='This is post 2b', community=community1, author=user2)
        post3a = Post(title='Post 3a', content='This is post 3a', community=community1, author=user3)
        post3b = Post(title='Post 3b', content='This is post 3b', community=community1, author=user3)
        post3c = Post(title='Post 3c', content='This is post 3c', community=community1, author=user3)

        # 1 post in Unpopular Community
        unpopular_post = Post(title='Unpopular Post', content='An unpopular post', community=community2, author=user1)

        # each user likes lower #'d user's posts
        post1a.likes.append(user2)
        post1a.likes.append(user3)
        post2a.likes.append(user3)
        post2b.likes.append(user3)

        # Old but highly liked post
        popular_post = Post(title='Old but popular post', content='Wow', community=community1, author=user1)
        popular_post.created_at = datetime.now() - timedelta(days=5)
        popular_post.likes.append(user1)
        popular_post.likes.append(user2)
        popular_post.likes.append(user3)

        # each user comments on the next user's #a post
        comment1 = Comment(content='This is comment 1 on post 2a', post=post2a, author=user1)
        comment2 = Comment(content='This is comment 2 on post 3a', post=post3a, author=user2)
        comment3 = Comment(content='This is comment 3 on post 1a', post=post1a, author=user3)

        # each user likes all other comments
        comment1.likes.append(user2)
        comment1.likes.append(user3)
        comment2.likes.append(user1)
        comment2.likes.append(user3)
        comment3.likes.append(user1)
        comment3.likes.append(user2)

        # add and commit everything
        db.session.add(user1)
        db.session.add(user2)
        db.session.add(user3)

        db.session.add(community1)
        db.session.add(community2)

        stagger_add([
            post1a,
            post2a,
            post2b,
            post3a,
            post3b,
            post3c,
            unpopular_post,
        ])

        stagger_add([
            comment1,
            comment2,
            comment3
        ])

        db.session.commit()

        print('Database initialized with test data.')
