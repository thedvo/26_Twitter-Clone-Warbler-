from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, EmailField, URLField
from wtforms.validators import DataRequired, Email, Length, Optional, InputRequired, URL


class MessageForm(FlaskForm):
    """Form for adding/editing messages."""

    text = TextAreaField('text', validators=[InputRequired()])


class UserAddForm(FlaskForm):
    """Form for adding users."""

    username = StringField('Username', validators=[InputRequired()])
    email = StringField('E-mail', validators=[InputRequired(), Email()])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=6)])
    image_url = StringField('Image URL', validators=[Optional(), URL()])


class LoginForm(FlaskForm):
    """Login form."""

    username = StringField('Username', validators=[InputRequired()])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=6)])


class EditUserForm(FlaskForm):
    """For for editing user profile"""

    username = StringField('Username', validators=[InputRequired()])
    email = StringField('E-mail', validators=[InputRequired(), Email()])
    image_url = StringField('Image URL', validators=[Optional(), URL()])
    header_image_url = StringField('Header Image URL', validators=[Optional(), URL()])
    location = StringField('Location', validators=[Optional()])
    bio = TextAreaField('Bio', validators=[Optional()])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=6)])
