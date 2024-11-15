"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


from app import app
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


# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class UserModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""
        db.drop_all()
        db.create_all()

        self.uid1 = 1111
        self.u1 = User.signup("test1", "email1@email.com", "password", None, bio="I am good looking", location= "Canada",header_image_url="http:google.com")
        
        self.u1.id = self.uid1

        self.u2 = User.signup("test2", "email2@email.com", "password", None,"Good mentor", location= "Canada",header_image_url="http")
        uid2 = 2222
        self.u2.id = uid2

        db.session.commit()

        self.u1 = User.query.get(self.uid1)
        self.u2 = User.query.get(uid2)

        self.client = app.test_client()

    def tearDown(self):
        # res = super().tearDown()
        # db.session.rollback()
        # return res
        db.session.remove()
        db.drop_all()
        db.create_all()
        super().tearDown()

    def test_user_model(self):
        """Does basic model work?"""

        u = User.signup(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD",
            image_url=None,
            bio= "test",
            location= "Russia",
            header_image_url= "http://"
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)

    ####
    #
    # Following tests
    #
    ####
    def test_user_follows(self):
        self.u1.following.append(self.u2)
        db.session.commit()

        self.assertEqual(len(self.u2.following), 0)
        self.assertEqual(len(self.u2.followers), 1)
        self.assertEqual(len(self.u1.followers), 0)
        self.assertEqual(len(self.u1.following), 1)

        self.assertEqual(self.u2.followers[0].id, self.u1.id)
        self.assertEqual(self.u1.following[0].id, self.u2.id)

    def test_is_following(self):
        self.u1.following.append(self.u2)
        db.session.commit()

        self.assertTrue(self.u1.is_following(self.u2))
        self.assertFalse(self.u2.is_following(self.u1))

    def test_is_followed_by(self):
        self.u1.following.append(self.u2)
        db.session.commit()

        self.assertTrue(self.u2.is_followed_by(self.u1))
        self.assertFalse(self.u1.is_followed_by(self.u2))

    ####
    #
    # Signup Tests
    #
    ####
    def test_valid_signup(self):
        u_test = User.signup(
            "testtesttest", "testtest@test.com", "password", None,bio="I am good looking", location= "Canada",header_image_url="http:google.com")
        uid = 99999
        u_test.id = uid
        db.session.commit()

        u_test = User.query.get(uid)
        self.assertIsNotNone(u_test)
        self.assertEqual(u_test.username, "testtesttest")
        self.assertEqual(u_test.email, "testtest@test.com")
        self.assertNotEqual(u_test.password, "password")
        # Bcrypt strings should start with $2b$
        self.assertTrue(u_test.password.startswith("$2b$"))
        


    def test_invalid_username_signup(self):
        with self.assertRaises((exc.IntegrityError, ValueError)) as context:
            User.signup(username= None, email="test@test.com", password="password", image_url= None, bio="I am good looking", location="Canada", header_image_url="http:google.com")
            db.session.commit()


    def test_invalid_email_signup(self):
        with self.assertRaises((exc.IntegrityError, ValueError)) as context:
            User.signup(username="testtest", email=None, password="password", bio="I am good looking", location="Canada",image_url = None,
            header_image_url="http:google.com")
            db.session.commit()



    def test_invalid_password_signup(self):
        with self.assertRaises(ValueError) as context:
            User.signup("testtest", "email@email.com", "", None,bio="I am good looking", location= "Canada",header_image_url="http:google.com")
            db.session.commit()

    ####
    #
    # Authentication Tests
    #
    ####
    def test_valid_authentication(self):
        u = User.authenticate(self.u1.username, "password")
        self.assertIsNotNone(u)
        self.assertEqual(u.id, self.uid1)

    def test_invalid_username(self):
        self.assertFalse(User.authenticate("badusername", "password"))

    def test_wrong_password(self):
        self.assertFalse(User.authenticate(self.u1.username, "badpassword"))
