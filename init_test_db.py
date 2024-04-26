from server import app, db
from server.models.user import *
from server.models.post import *

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

        # user1 has a discord account connected
        user1_discord = ConnectedAccount(
            provider=OAuthProvider.DISCORD,
            username='user1_but_on_discord',
            access_token='access_token1',
            user=user1,
            expires_at=datetime.now()
        )

        # 2 default communities, 1 with all users in it and another empty
        community1 = Community(name='Popular Community')
        community2 = Community(name='Unpopular Community')

        community1.users.append(user1)
        community1.users.append(user2)
        community1.users.append(user3)

        # user 1 has 1 post, user 2 has 2, etc.
        post1a = Post(title='Post 1a', content='This is post 1a', community=community1, author=user1)
        post2a = Post(title='Post 2a', content='This is post 2a', community=community1, author=user2)
        post2b = Post(title='Post 2b', content='This is post 2b', community=community1, author=user2)
        post3a = Post(title='Post 3a', content='This is post 3a', community=community1, author=user3)
        post3b = Post(title='Post 3b', content='This is post 3b', community=community1, author=user3)
        post3c = Post(title='Post 3c', content='This is post 3c', community=community1, author=user3)

        # each user likes lower #'d user's posts
        post1a.likes.append(user2)
        post1a.likes.append(user3)
        post2a.likes.append(user3)
        post2b.likes.append(user3)

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

        db.session.add(user1_discord)

        db.session.add(community1)
        db.session.add(community2)

        db.session.add(post1a)
        db.session.add(post2a)
        db.session.add(post2b)
        db.session.add(post3a)
        db.session.add(post3b)
        db.session.add(post3c)

        db.session.add(comment1)
        db.session.add(comment2)
        db.session.add(comment3)

        db.session.commit()

        print('Database initialized with test data.')
