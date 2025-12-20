from flask import current_app
from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import BooleanField, HiddenField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from itsdangerous import URLSafeTimedSerializer, BadSignature

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
    website = StringField(_l("Website"), validators=[Length(max=64)])
    # Timestamp field - to prevent fast submissions (bots)
    timestamp = HiddenField()
    submit = SubmitField(_l("Register"))

    def validate_website(self, website):
        if website.data:
            raise ValidationError(_l("Spam detected."))

    def validate_timestamp(self, timestamp):
        if not timestamp.data:
            raise ValidationError(_l("Spam detected."))

        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            # Check if timestamp is younger than 3 seconds
            # max_age is not used here because we want MINIMUM age
            data = s.loads(timestamp.data)
            # data should be the time.time() when form was generated
            # Wait, `loads` returns the data. We signed a timestamp or just 'register'?
            # Let's sign the current time.
            # Actually, `dumps(time.time())`.
            # But wait, `loads` doesn't check age automatically unless we use `loads(..., max_age=...)`.
            # We want to check if `now - timestamp < 3`.

            # Let's assume we store the timestamp float.
            import time

            submission_time = time.time()
            generation_time = float(data)

            if submission_time - generation_time < 3:
                raise ValidationError(
                    _l("Form submitted too quickly. Please try again.")
                )

            # Also check if it's too old? (e.g. > 1 hour) - optional but good practice
            if submission_time - generation_time > 3600:
                raise ValidationError(_l("Form session expired. Please refresh."))

        except (BadSignature, ValueError, TypeError):
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
