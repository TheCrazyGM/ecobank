from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional


class AdminUserEditForm(FlaskForm):
    username = StringField(
        _l("Username"), validators=[DataRequired(), Length(min=3, max=64)]
    )
    email = StringField(
        _l("Email"), validators=[DataRequired(), Email(), Length(max=120)]
    )
    account_credits = IntegerField(_l("Credits"), validators=[Optional()])
    # Optional password field for admin reset
    password = PasswordField(_l("New Password"), validators=[Optional(), Length(min=6)])
    submit = SubmitField(_l("Update User"))


class AdminGroupEditForm(FlaskForm):
    name = StringField(_l("Group Name"), validators=[DataRequired()])
    description = TextAreaField(_l("Description"))
    default_tags = StringField(_l("Default Tags"), validators=[Optional()])
    owner_username = StringField(_l("Owner Username"), validators=[DataRequired()])
    submit = SubmitField(_l("Update Group"))
