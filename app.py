import os

# Set the environment to production
os.environ['FLASK_ENV'] = 'production'

from flask import Flask, render_template, request, flash, redirect, session, g, url_for, abort
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, LoginForm, MessageForm
from models import db, connect_db, User, Message


CURR_USER_KEY = "curr_user"

app = Flask(__name__)
# app.app_context().push()

# app_ctxt = app.app_context()
# app_ctxt.push()

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgresql:///warbler'))


app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
def connect_db(app):
    with app.app_context():
        db.app = app
        db.init_app(app)
        db.create_all()
app.config['DEBUG_TB_ENABLED'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")

toolbar = DebugToolbarExtension(app)

connect_db(app)

# Print the current Flask environment
current_env = os.environ.get('FLASK_ENV', 'default')
print(f"Running in {current_env} mode")
##############################################################################
# User signup/login/logout

@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If there already is a user with that username: flash message
    and re-present form.
    """

    form = UserAddForm()

    if form.validate_on_submit():
        # Check if the email or username is already taken
        existing_user = User.query.filter(
            (User.username == form.username.data) and 
            (User.email == form.email.data)
        ).first()
        existing_username = User.query.filter(
            (User.username == form.username.data)).first()
        existing_email = User.query.filter(User.email == form.email.data).first()
        if existing_user:
            flash('Username and email already taken', 'danger')
            return render_template('users/signup.html', form=form)
        elif existing_username:
            flash('Username already taken', 'danger')
            return render_template('users/signup.html', form=form)
        elif existing_email:
            flash('Email already taken', 'danger')
            return render_template('users/signup.html', form=form)
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
                bio=form.bio.data,
                location=form.location.data,
                header_image_url=form.header_image_url.data or User.header_image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            db.session.rollback()
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)
        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)



@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""

    # IMPLEMENT THIS
    do_logout()  # This function will remove the CURR_USER_KEY from the session
    flash('Successfully logged out','success')
    return redirect("/login")
    

##############################################################################
# General user routes:

@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile."""
    
    user = User.query.get_or_404(user_id)

    # snagging messages in order from the database;
    # user.messages won't be in order by default

    #If the user is not logged in
    if g.user is None:
        flash("Access unauthorized.", "danger")
        print("g.user is not logged in")
        return redirect("/login")
    
    #If the user that is logged in tries to change their user id to access another user id
    if g.user.id != user_id:
        flash("Access unauthorized.", "danger")
        print(">>>>>>>>>>>>>>>>>>>>>>second option")
        return redirect(url_for("homepage"))

    messages = (Message
                .query
                .filter(Message.user_id == user_id)
                .order_by(Message.timestamp.desc())
                .limit(100)
                .all())
    return render_template('users/show.html', user=user, messages=messages)


@app.route('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/following.html', user=user)


@app.route('/users/<int:user_id>/followers')
def users_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)


@app.route('/users/follow/<int:follow_id>', methods=['POST'])
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/profile', methods=["GET", "POST"])
def profile():
    """Update profile for current user."""

    # IMPLEMENT THIS
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    user = g.user
    form = UserAddForm(obj=user)

    if form.validate_on_submit():
        if User.authenticate(user.username, form.password.data):
            user.username = form.username.data
            user.email = form.email.data
            user.image_url = form.image_url.data or "/static/images/default-pic.png"
            user.bio = form.bio.data
            user.location = form.location.data
            user.header_image_url = form.header_image_url.data or "/static/images/warbler-hero.jpg"
            

            db.session.commit()
            return redirect(f"/users/{user.id}")

        flash("Wrong password, please try again.", 'danger')
        return redirect(url_for('homepage'))

    return render_template('users/edit.html', form=form, user_id=user.id)

@app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")


##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
def add_message():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """
    
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")
    else:
        print("Form errors:", form.errors)  # This will print any form validation errors

    return render_template('messages/new.html', form=form)

@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""

    msg = Message.query.get(message_id)
    if msg is None:
        # Return a 404 Not Found response if there is no message with the given ID
        abort(404)
    return render_template('messages/show.html', message=msg)


@app.route('/users/add_like/<int:message_id>' , methods=['GET','POST'])
def like_message(message_id):
    """Toggle a liked message for the currently-logged-in user."""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    liked_message = Message.query.get_or_404(message_id)
    if liked_message.user_id == g.user.id:
        return abort(403)

    user_likes = g.user.likes

    if liked_message in user_likes:
        g.user.likes = [like for like in user_likes if like != liked_message]
    else:
        g.user.likes.append(liked_message)

    db.session.commit()

    return redirect("/")

@app.route('/users/<int:user_id>/likes', methods=["GET"])
def show_likes(user_id):
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/likes.html', user=user, likes=user.likes)

@app.route('/messages/<int:message_id>/delete', methods=["POST"])
def delete_message(message_id):
    """Delete a message."""

    # First, check if a user is logged in
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    # Retrieve the message by ID
    msg = Message.query.get_or_404(message_id)  # This will abort with a 404 error if no message found

    # Check if the message belongs to the current user
    if msg.user_id != g.user.id:
        flash("Access unauthorized.", "danger")
        return redirect('/')

    # If checks pass, delete the message
    db.session.delete(msg)
    db.session.commit()

    flash("Message deleted.", "success")
    return redirect(f"/users/{g.user.id}")

##############################################################################
# Homepage and error pages


@app.route('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """

    if g.user:

        following_ids = [f.id for f in g.user.following] + [g.user.id]

        messages = (Message
                    .query
                    .filter(Message.user_id.in_(following_ids))
                    .order_by(Message.timestamp.desc())
                    .limit(100)
                    .all())

        return render_template('home.html', messages=messages)

    else:
        return render_template('home-anon.html')


##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req

@app.cli.command() 
def test():
    """Run the unit tests."""
    import unittest
    # tests = unittest.TestLoader().discover('tests')
    # unittest.TextTestRunner(verbosity=2).run(tests)

# To create table that are in models.py
with app.app_context():
    db.create_all()