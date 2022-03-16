"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User

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


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)

        self.testuser_id = 1000
        self.testuser.id = self.testuser_id                          

        db.session.commit()

    def tearDown(self):
        """Clean up any foul transaction."""

        db.session.rollback()
    

#######################################################################
# ADDING A MESSAGE

    def test_add_message(self):
        """Can use add a message?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.post("/messages/new", data={"text": "Hello"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            msg = Message.query.one()
            self.assertEqual(msg.text, "Hello")

    def test_add_message_notloggedin(self):
        """Tests if user can add a message if not logged in"""

        with self.client as client:
            res = client.post("/messages/new", 
                         data={"text": "Hello"}, 
                         follow_redirects=True)

            self.assertEqual(res.status_code, 200)
            self.assertIn("Access unauthorized", str(res.data))

    def test_add_message_as_invalid_user(self):
        """Tests if user can add a message on another user's account"""

        with self.client as client:
            with client.session_transaction() as session:
                session[CURR_USER_KEY] = 100
                # user not in database

            res = client.post("/messages/new", 
                         data={"text": "Hello"}, 
                         follow_redirects=True)

            self.assertEqual(res.status_code, 200)
            self.assertIn("Access unauthorized", str(res.data))
            
#######################################################################
# SHOW A MESSAGE 
    
    def test_show_message(self):
        """Show a valid message"""

        message = Message(
            id=1000,
            text="another message to test",
            user_id=self.testuser_id
        )
        
        db.session.add(message)
        db.session.commit()

        with self.client as client:
            with client.session_transaction() as session:
                session[CURR_USER_KEY] = self.testuser.id
            
            message = Message.query.get(1000)

            res = client.get(f'/messages/{message.id}')

            self.assertEqual(res.status_code, 200)
            self.assertIn(message.text, str(res.data))


    def test_show_invalid_message(self):
        """Try to route to a message that doesn't exist in database"""
        with self.client as client:
            with client.session_transaction() as session:
                session[CURR_USER_KEY] = self.testuser.id
            
            res = client.get('/messages/100000')

            self.assertEqual(res.status_code, 404)

#######################################################################
# DELETE A MESSAGE

    def test_delete_message(self):
        """Test deleting a message"""
        
        message = Message(
            id=123456,
            text="another test message",
            user_id=self.testuser_id
        )
        db.session.add(message)
        db.session.commit()

        with self.client as client:
            with client.session_transaction() as session:
                session[CURR_USER_KEY] = self.testuser.id

            res = client.post("/messages/123456/delete", 
                              follow_redirects=True)
            self.assertEqual(res.status_code, 200)

            message = Message.query.get(123456)
            self.assertIsNone(message)


    def test_delete_message_as_unauthorized_user(self):
        """A user should not be able to delete another user's messages"""

        # this will be the unauthorized user
        new_user = User.signup(
                   username = 'bad_user',
                   email = "test4@test.com",
                   password = "HASHED_PASSWORD",
                   image_url = None
        )
        new_user.id = 99999

        db.session.add(new_user)
        db.session.commit()

        # create message for the original testuser that we can use to delete
        message = Message(
            id = 1001,
            text = "another test message",
            user_id = self.testuser.id
        )

        db.session.add(message)
        db.session.commit()

        with self.client as client:
            with client.session_transaction() as session:
                session[CURR_USER_KEY] = 99999
                # we want to use the user ID of the unauthorized user 

            res = client.post('/messages/1001/delete',
                              follow_redirects = True)

            message = Message.query.get(1001)


            self.assertEqual(res.status_code, 200)
            self.assertIn("Access unauthorized", str(res.data))
            self.assertIsNotNone(message)
            # should be not none since we didn't actually delete the message

    def test_delete_message_with_no_authentication(self):

        message = Message(
            id=123456,
            text="another test",
            user_id=self.testuser_id
        )
        db.session.add(message)
        db.session.commit()

        with self.client as client:
            res = client.post("/messages/123456/delete", 
                               follow_redirects=True)

            self.assertEqual(res.status_code, 200)
            self.assertIn("Access unauthorized", str(res.data))

            message = Message.query.get(123456)
            self.assertIsNotNone(message)

        