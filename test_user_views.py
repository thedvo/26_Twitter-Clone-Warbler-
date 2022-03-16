"""User View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py

import os
from unittest import TestCase

from models import db, connect_db, Message, User, Likes, Follows


# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class UserViewTestCase(TestCase):
    """Test views for Users."""
    
    def setUp(self):
        """Create test client, add sample data."""

        db.drop_all()
        db.create_all()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)
        self.testuser_id = 9999
        self.testuser.id = self.testuser_id

        self.user1 = User.signup("one", 
                              "one@test.com", 
                              "password", 
                               None)
        self.user1.id = 1111

        self.user2 = User.signup("two", 
                              "two@test.com", 
                              "password", 
                               None)
        self.user2.id = 2222

        self.user3 = User.signup("three", 
                              "three@test.com", 
                              "password", 
                               None)
        self.user3.id = 3333

        db.session.commit()


    def tearDown(self):
        """Clean up any foul transaction."""

        db.session.rollback()

###############################################################################################
# USER ROUTES

    def test_list_all_users(self):
        """Route to list of users"""
        with self.client as client:
            res = client.get("/users")

            self.assertIn("@testuser", str(res.data))
            self.assertIn("@one", str(res.data))
            self.assertIn("@two", str(res.data))
            self.assertIn("@three", str(res.data))
      
    def test_search_user(self):
        """Search user route"""

        with self.client as client:
            res = client.get("/users?q=t")

            self.assertIn("@testuser", str(res.data))
            self.assertIn("@two", str(res.data))
            self.assertIn("@three", str(res.data))
            self.assertNotIn("@one", str(res.data))

    def test_show_user(self):
        """Show User"""
        with self.client as client:
            res = client.get(f"/users/{self.testuser_id}")

            self.assertEqual(res.status_code, 200)
            self.assertIn("@testuser", str(res.data))
    
###############################################################################################
# LIKE ROUTES

    def setup_likes(self):
        """set up messages and likes to use in tests"""
        message1 = Message(text="I like pizza", 
                           user_id=self.testuser_id)

        message2 = Message(id = 22222,
                           text="I like burritos", 
                           user_id=self.user1.id)
       
        db.session.add_all([message1, message2])
        db.session.commit()

        like = Likes(user_id=self.testuser_id, 
                      message_id=22222)

        db.session.add(like)
        db.session.commit()

    def test_like_message(self):
        """Add like to a message"""
        
        # create a message that will be liked
        message = Message(id = 11111,
                          text = "I like sandwiches", 
                          user_id = self.testuser_id)

        db.session.add(message)
        db.session.commit()

        # create a user who will like the created message 
        new_user = User.signup(
                   username = 'new_user',
                   email = "test4@test.com",
                   password = "HASHED_PASSWORD",
                   image_url = None
        )
        new_user.id = 999999

        db.session.add(new_user)
        db.session.commit()

        # set session to be logged in as the created user
        with self.client as client:
            with client.session_transaction() as session:
                session[CURR_USER_KEY] = 999999

            # make post request (like) for that created message
            res = client.post("/messages/11111/like",
                              follow_redirects=True)

            likes = Likes.query.filter(Likes.message_id==11111).all()

            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(likes), 1)
            self.assertEqual(likes[0].user_id, 999999)

    
    def test_remove_like(self):
        """Removing a like from a message"""
        self.setup_likes()

        # get the liked message 
        message = Message.query.filter(Message.text=="I like burritos").one()
        self.assertIsNotNone(message)
        # should not be a message created by the logged in user
        self.assertNotEqual(message.user_id, self.testuser_id)

        # query the message which is liked by the logged in user
        like = Likes.query.filter(Likes.user_id==self.testuser_id and Likes.message_id==message.id).one()

        # check if there is a like
        self.assertIsNotNone(like)

        
        with self.client as client:
            with client.session_transaction() as session:
                session[CURR_USER_KEY] = self.testuser_id

            # we will make another post request to like that message so we can unlike it. 
            res = client.post(f"/messages/{message.id}/like", 
                              follow_redirects=True)

            likes = Likes.query.filter(Likes.message_id==message.id).all()

            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(likes), 0)



    def test_like_message_unauthorized_user(self):
        """Making a like while not signed in"""
        self.setup_likes()

        # select a message
        message = Message.query.filter(Message.text=="I like burritos").one()
        self.assertIsNotNone(message)

        # count the number of likes there are
        like_count = Likes.query.count()

        # now try to make a post request to make a like to that selected message
        with self.client as client:
            res = client.post(f"/messages/{message.id}/like",           
                              follow_redirects=True)

            self.assertEqual(res.status_code, 200)
            self.assertIn("Access unauthorized", str(res.data))
            # access unauthorized since user is not logged in
            self.assertEqual(like_count, Likes.query.count())
            # number of likes should not change since user is unauthorized to make this request

###############################################################################################
# FOLLOWER/FOLLOWING ROUTES

    def setup_followers(self):
        """Set up followers to use in tests"""

        # testuser follows user1
        follow1 = Follows(user_being_followed_id=self.user1.id, 
                    user_following_id=self. testuser_id)

        # testuser follows user2
        follow2 = Follows(user_being_followed_id=self.user2.id, 
                    user_following_id=self.testuser_id)

        # user1 follows testuser
        follow3 = Follows(user_being_followed_id=self.testuser_id, 
                    user_following_id=self.user1.id)

        db.session.add_all([follow1, follow2, follow3])
        db.session.commit()


    def test_show_following(self):
        """show user's following list"""

        self.setup_followers()

        with self.client as client:
            with client.session_transaction() as session:
                session[CURR_USER_KEY] = self.testuser_id

            res = client.get(f"/users/{self.testuser_id}/following")

            self.assertEqual(res.status_code, 200)
            self.assertIn("@one", str(res.data))
            self.assertNotIn("@three", str(res.data))   


    def test_show_followers(self):
        """show user's followers list"""

        self.setup_followers()

        with self.client as client:
            with client.session_transaction() as session:
                session[CURR_USER_KEY] = self.testuser_id

            res = client.get(f"/users/{self.testuser_id}/followers")

            # since user1 follows testuser, it should show in the response
            self.assertIn("@one", str(res.data))
            self.assertNotIn("@two", str(res.data))
            self.assertNotIn("@three", str(res.data))


    def test_show_following_page__unauthorized(self):
        """Users not logged in should not be able to see a user's following page"""
        
        self.setup_followers()
        
        with self.client as client:
            res = client.get(f"/users/{self.testuser_id}/following", 
                             follow_redirects=True)

            self.assertEqual(res.status_code, 200)
            self.assertIn("Access unauthorized", str(res.data))
            self.assertNotIn("@one", str(res.data))


    def test_followers_page_unauthorized(self):
        """Users not logged in should not be able to see a user's followers page"""
        
        self.setup_followers()
        
        with self.client as client:

            res = client.get(f"/users/{self.testuser_id}/followers", 
                             follow_redirects=True)

            self.assertEqual(res.status_code, 200)
            self.assertIn("Access unauthorized", str(res.data))
            self.assertNotIn("@one", str(res.data))


    def test_add_follow(self):
        """test user following another user"""

        with self.client as client:
            with client.session_transaction() as session:
                session[CURR_USER_KEY] = self.user2.id

            res = client.post(f"/users/follow/{self.testuser_id}", 
                             follow_redirects=True)

            self.assertEqual(res.status_code, 200)
            self.assertNotIn("@one", str(res.data))
        

    def test_remove_follow(self):
        """test user unfollowing another user"""

        self.setup_followers()

        with self.client as client:
            with client.session_transaction() as session:
                session[CURR_USER_KEY] = self.user1.id

            res = client.post(f"/users/stop-following/{self.testuser_id}", 
                             follow_redirects=True)

            self.assertEqual(res.status_code, 200)
            self.assertNotIn("@testuser", str(res.data))

###############################################################################################
