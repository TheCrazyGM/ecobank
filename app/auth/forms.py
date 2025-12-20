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
    username = StringField(
        _l("Username"), validators=[DataRequired(), Length(min=3, max=64)]
    )
    email = StringField(
        _l("Email"), validators=[DataRequired(), Email(), Length(max=120)]
    )
    password = PasswordField(_l("Password"), validators=[DataRequired()])
    confirm_password = PasswordField(
        _l("Repeat Password"), validators=[DataRequired(), EqualTo("password")]
    )
    # Honeypot field - should be left empty by humans
    hp_field = StringField(_l("Middle Name"), validators=[Length(max=64)])
    submit = SubmitField(_l("Register"))

    def validate_hp_field(self, hp_field):
        if hp_field.data:
            raise ValidationError(_l("Spam detected."))

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError(_l("Please use a different username."))

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError(_l("Please use a different email address."))


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        _l("Current Password"), validators=[DataRequired()]
    )
    new_password = PasswordField(
        _l("New Password"), validators=[DataRequired(), Length(min=6)]
    )
    confirm_password = PasswordField(
        _l("Confirm New Password"), validators=[DataRequired(), EqualTo("new_password")]
    )
    submit = SubmitField(_l("Change Password"))


class ResetPasswordRequestForm(FlaskForm):
    email = StringField(_l("Email"), validators=[DataRequired(), Email()])
    submit = SubmitField(_l("Request Password Reset"))


class ResetPasswordForm(FlaskForm):
    password = PasswordField(_l("Password"), validators=[DataRequired()])
    repeat_password = PasswordField(
        _l("Repeat Password"), validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField(_l("Request Password Reset"))


class ResendVerificationRequestForm(FlaskForm):
    email = StringField(_l("Email"), validators=[DataRequired(), Email()])
    submit = SubmitField(_l("Resend Verification Email"))
