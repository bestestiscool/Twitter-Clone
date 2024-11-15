# """Seed database with sample data from CSV Files."""

# from csv import DictReader
# from models import db, User, Message, Follows

# app_ctxt = app.app_context()
# app_ctxt.push()
# def seed(app):
#     with app.app_context():
#         db.drop_all()
#         db.create_all()

#         with open('generator/users.csv') as users:
#             db.session.bulk_insert_mappings(User, DictReader(users))

#         with open('generator/messages.csv') as messages:
#             db.session.bulk_insert_mappings(Message, DictReader(messages))

#         with open('generator/follows.csv') as follows:
#             db.session.bulk_insert_mappings(Follows, DictReader(follows))

#         db.session.commit()

#         print("Database seeded!")

"""Seed database with sample data from CSV Files."""

from csv import DictReader
from app import app
from models import User, Message, Follows


def seed(db):
    with db.app.app_context():
        db.drop_all()
        db.create_all()

        with open('generator/users.csv') as users:
            db.session.bulk_insert_mappings(User, DictReader(users))

        with open('generator/messages.csv') as messages:
            db.session.bulk_insert_mappings(Message, DictReader(messages))

        with open('generator/follows.csv') as follows:
            db.session.bulk_insert_mappings(Follows, DictReader(follows))

        db.session.commit()

        print("Database seeded!")

if __name__ == '__main__':
    from app import db  # Import db here to avoid circular import
    seed(db)
