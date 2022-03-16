"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py

import os
from unittest import TestCase
from sqlalchemy import exc


from models import db, User, Message, Follows

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.drop_all()
db.create_all()


class UserModelTestCase(TestCase):
    """Test User Model"""

    def setUp(self):
        """Create test client, add sample data."""
        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        user1 = User.signup("test@test.com", "testuser", "HASHED_PASSWORD", None)
        user1.id = 10

        user2 = User.signup("test2@test.com", "testuser2", "HASHED_PASSWORD2", None)
        user2.id = 20

        db.session.commit()

        user1 = User.query.get(user1.id)
        user2 = User.query.get(user2.id)


        self.user1  = user1
        self.user1_id = user1.id

        self.user2 = user2
        self.user2_id = user2.id

        self.client = app.test_client()


    def tearDown(self):
        """Clean up any foul transaction."""

        db.session.rollback()


    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)
        self.assertEqual(u.__repr__(), "<User #1: testuser, test@test.com>")


############################################################################
# FOLLOWING TESTS

    def test_is_following(self):
        """Detects if user1 follows user2"""

        add_follow = Follows(user_being_followed_id = 20, 
                         user_following_id = 10)

        db.session.add(add_follow)
        db.session.commit()

        self.assertEqual(self.user1.is_following(self.user2), 1)
        self.assertEqual(self.user2.is_following(self.user1), 0)

    def test_is_followed_by(self):
        """Detects if user1 is followed by user2"""

        add_follow = Follows(user_being_followed_id = 10, 
                         user_following_id = 20)

        db.session.add(add_follow)
        db.session.commit()

        self.assertEqual(self.user2.is_following(self.user1), 1)
        self.assertEqual(self.user1.is_following(self.user2), 0)

############################################################################

# SIGNUP TESTS

    def test_create_user_valid(self):
        """Successfully create new user given valid credentials"""

        new_user = User.signup("testuser3", 
                               "test3@test.com", 
                               "HASHED_PASSWORD3", 
                                None)
        uid = 30
        new_user.id = uid

        db.session.commit()

        new_user = User.query.get(new_user.id)
        self.assertIsNotNone(new_user)
        self.assertEqual(new_user.username, "testuser3")
        self.assertEqual(new_user.email, "test3@test.com")
        self.assertNotEqual(new_user.password, "HASHED_PASSWORD3")
        # reason we test for not equal is because it should be encrypted



    def test_create_user_invalid_username(self):
        """Tests if user creation fails if username validation fails."""

        invalid_user = User.signup( None,                          
                                    "test@test.com", 
                                    "HASHED_PASSWORD", 
                                    None)
        uid = 40
        invalid_user.id = uid
        
        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()


    def test_create_user_invalid_email(self):
        """Testing if validation checks if there is a valid email inputted"""
        invalid = User.signup("test", 
                               None, 
                               "HASHED_PASSWORD", 
                               None)
        uid = 50
        invalid.id = uid
        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()

    def test_create_user_invalid_password(self):
        """Testing if validation checks if there is a valid password inputted"""

        with self.assertRaises(ValueError) as context:
            User.signup("test", 
                        "test@test.com", 
                        "", 
                        None)
        
############################################################################

# AUTHENTICATION TESTS

    def test_authentication(self):
        """Successful return given valid username and password"""
        user = User.authenticate(self.user1.username, "HASHED_PASSWORD")
        
        self.assertIsNotNone(user)
        self.assertEqual(user.id, self.user1_id)


        
    def test_invalid_username(self):
        """Failure given invalid username"""
        
        self.assertFalse(User.authenticate("invalid_username", "password"))


    def test_invalid_password(self):
        """Failure given invalid password"""
        
        self.assertFalse(User.authenticate(self.user1.username, "wrongpassword"))

