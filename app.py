
from flask import Flask, render_template, request, flash, redirect, session, g, abort
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, LoginForm, MessageForm, EditUserForm
from models import db, connect_db, User, Message
import os
import re


CURR_USER_KEY = "curr_user"

app = Flask(__name__)


uri = os.environ.get('DATABASE_URL', 'postgresql:///warbler')
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = uri


app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False 
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
toolbar = DebugToolbarExtension(app)

connect_db(app)

###################################################################
# ERROR HANDLERS

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

##############################################################################
# User signup/login/logout


@app.before_request   # This function is run before each request. 
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])
        # if there is currently a logged in user, query that user 
        # A common use for 'g' is to manage resources during a request. The g name stands for “global”, but that is referring to the data being global within a context.
        # Use the session or a database to store data across requests. The application context is a good place to store common data during a request.

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

    If the there already is a user with that username: flash message
    and re-present form.
    """

    if g.user:
        flash("Already logged in. If you would like to make another account, please logout of the current account.", "danger")
        return redirect("/")

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken. Please try a different username.", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    if g.user: 
        flash("You are currently logged in.", "danger")
        return redirect("/")


    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Welcome back, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""

    if not g.user:
        flash("You need to log in or sign up for an account.", "danger")
        return redirect("/")

    do_logout() # this method is defined above

    flash(f"You have successfully logged out.", "success")
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
    messages = (Message
                .query
                .filter(Message.user_id == user_id)
                .order_by(Message.timestamp.desc())
                .limit(100)
                .all())

    # shows the likes of the current user
    if g.user:
        likes = [message.id for message in g.user.likes]
        
        return render_template('users/show.html', user=user, messages=messages, likes=likes)

    else:
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

    if g.user.id == follow_id:
        flash("You can't follow yourself!", "danger")
        return redirect('/')

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


###########################################################
# LIKE routes 
@app.route('/users/<int:user_id>/likes')
def show_likes(user_id):
    """Shows list of the user's liked messages"""

    if not g.user:
        flash('Access unauthorized.', 'danger')
        return redirect('/')

    user = User.query.get_or_404(user_id)

    return render_template('users/likes.html', user=user, likes=user.likes)


@app.route('/messages/<int:message_id>/like', methods=['POST'])
def add_like(message_id):
    """Adds/Removes like from a message"""

    if not g.user:
        flash('Access unauthorized.', 'danger')
        return redirect('/')

    liked_message = Message.query.get_or_404(message_id)

    # Checks if the message was created by the current user. If so, it will abort the request. 
    if liked_message.user_id == g.user.id:
        return abort(403) 
        # aborts a request with an HTTP error code early
    
    user_likes = g.user.likes


    if liked_message in user_likes:
        g.user.likes = [like for like in user_likes if like != liked_message]
    else: 
        g.user.likes.append(liked_message)

    db.session.commit()

    return redirect('/')


############################################################
@app.route('/users/profile', methods=["GET", "POST"])
def profile():
    """Update profile for current user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect('/')

    user = g.user
    form = EditUserForm(obj=user)

    if form.validate_on_submit():
        if User.authenticate(user.username, form.password.data):

            user.username = form.username.data
            user.email = form.email.data
            user.image_url = form.image_url.data or User.image_url.default.arg
            user.header_image_url = form.header_image_url.data or User.header_image_url.default.arg
            user.location = form.location.data
            user.bio = form.bio.data

            db.session.commit()

            flash("User profile successfully updated.", "success")

            return redirect(f"/users/{user.id}")
        
        flash("Wrong password, please try again.", 'danger')

    return render_template('users/edit.html', form=form, user_id=user.id)

#############################################################

@app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(g.user)
    db.session.commit()


    flash('User has been deleted.' , "success")
    return redirect("/signup")


##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
def messages_add():
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

    return render_template('messages/new.html', form=form)


@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""

    msg = Message.query.get_or_404(message_id)
    return render_template('messages/show.html', message=msg)


@app.route('/messages/<int:message_id>/delete', methods=["POST"])
def messages_destroy(message_id):
    """Delete a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get_or_404(message_id)
    if msg.user_id != g.user.id:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    db.session.delete(msg)
    db.session.commit()

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
        following_ids = [user.id for user in g.user.following] + [g.user.id] 
        # takes the id's of the users that the logged in user is following and the current user's ID
        # this makes it possible to filter the query so that we only show posts from users that the user is folling and the user's own posts in the homepage 

        messages = (Message
                    .query
                    .filter(Message.user_id.in_(following_ids)) # only queries messages that meet these criteria 
                    .order_by(Message.timestamp.desc())
                    .limit(100)
                    .all())

        liked_msg_ids = [msg.id for msg in g.user.likes]

        return render_template('home.html', messages=messages, likes=liked_msg_ids)

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
