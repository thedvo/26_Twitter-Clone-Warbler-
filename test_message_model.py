"""Message model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py

import os
from unittest import TestCase

from models import db, User, Message, Follows, Likes

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


class MessageModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        self.client = app.test_client()

        user = User.signup("test_user",
                           "test@test.com",
                           "HASH_PASSWORD",
                           None)
        self.user_id = 10
        user.id = self.user_id
        
        db.session.commit()

        self.user = User.query.get(self.user_id)
        

    def tearDown(self):
        db.session.rollback()


    def test_message_model(self):
        """Checks if message model works"""

        new_message = Message(
                      text = "first message",
                      user_id = self.user_id
        )

        db.session.add(new_message)
        db.session.commit()

        self.assertEqual(len(self.user.messages), 1)
        self.assertEqual(self.user.messages[0].text, "first message")

    
    def test_liking_message(self):
        message = Message(
                text = "this is a fun message",
                user_id = self.user_id
        )

        user = User.signup("imatester",
                           "tester@tester.com",
                           "password123",
                           None)
        user.id = 50

        db.session.add_all([message, user])
        db.session.commit()

        like = Likes(
                user_id = user.id,
                message_id = 1
        )

        db.session.add(like)
        db.session.commit()


        self.assertEqual(len(user.likes), 1)

