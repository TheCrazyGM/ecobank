from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length

from app.models import User

class LoginForm(FlaskForm):
    username = StringField(_l("Username"), validators=[DataRequired()])
    password = PasswordField(_l("Password"), validators=[DataRequired()])
    remember_me = BooleanField(_l("Remember Me"))
    submit = SubmitField(_l("Sign In"))

class RegistrationForm(FlaskForm):
    username = StringField(_l("Username"), validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField(_l("Email"), validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField(_l("Password"), validators=[DataRequired()])
    confirm_password = PasswordField(_l("Repeat Password"), validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField(_l("Register"))

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError(_l('Please use a different username.'))

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError(_l('Please use a different email address.'))

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(_l("Current Password"), validators=[DataRequired()])
    new_password = PasswordField(_l("New Password"), validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(_l("Confirm New Password"), validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField(_l("Change Password"))