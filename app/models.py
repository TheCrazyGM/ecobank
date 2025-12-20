from datetime import datetime, timezone, timedelta
import jwt
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from mongoengine import Document, StringField, IntField, DateTimeField

from app.extensions import db, login_manager


class User(UserMixin, db.Model):  # ty:ignore[unsupported-base]
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    locale = db.Column(db.String(2), default="en")
    account_credits = db.Column(db.Integer, default=0, nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    # Profile info for "About the Author"
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    bio = db.Column(db.Text)
    avatar_url = db.Column(db.String(256))

    hive_accounts = db.relationship("HiveAccount", backref="creator", lazy="dynamic")
    orders = db.relationship("PayPalOrder", backref="user", lazy="dynamic")

    # Group relationships
    created_groups = db.relationship("Group", backref="owner", lazy="dynamic")
    group_memberships = db.relationship("GroupMember", backref="user", lazy="dynamic")

    # Drafts
    drafts = db.relationship("Draft", backref="author", lazy="dynamic")

    # Notifications
    notifications = db.relationship("Notification", backref="user", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {
                "reset_password": self.id,
                "exp": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
            },
            current_app.config["SECRET_KEY"],
            algorithm="HS256",
        )

    def get_email_verification_token(self, expires_in=86400):
        return jwt.encode(
            {
                "verify_email": self.id,
                "exp": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
            },
            current_app.config["SECRET_KEY"],
            algorithm="HS256",
        )

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(
                token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
            )["reset_password"]
        except Exception:
            return None
        return db.session.get(User, id)

    @staticmethod
    def verify_email_verification_token(token):
        try:
            id = jwt.decode(
                token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
            )["verify_email"]
        except Exception:
            return None
        return db.session.get(User, id)

    @property
    def display_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    def __repr__(self):
        return f"<User {self.username}>"


class HiveAccount(db.Model):  # ty:ignore[unsupported-base]
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(16), index=True, unique=True)
    password_enc = db.Column(db.Text)  # Encrypted password
    keys_enc = db.Column(db.Text)  # Encrypted JSON keys
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    tx_id = db.Column(db.String(64))


class PayPalOrder(db.Model):  # ty:ignore[unsupported-base]
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    paypal_order_id = db.Column(db.String(64), unique=True)
    amount = db.Column(db.Float)
    currency = db.Column(db.String(3), default="USD")
    status = db.Column(db.String(20), default="CREATED")  # CREATED, COMPLETED, FAILED
    credits_purchased = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )


class Group(db.Model):  # ty:ignore[unsupported-base]
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    description = db.Column(db.Text)
    default_tags = db.Column(db.String(256))
    owner_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(
        db.DateTime, default=datetime.now(timezone.utc), nullable=False
    )

    members = db.relationship(
        "GroupMember", backref="group", cascade="all, delete-orphan"
    )
    resources = db.relationship(
        "GroupResource", backref="group", cascade="all, delete-orphan"
    )
    drafts = db.relationship("Draft", backref="group", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Group {self.name}>"

    @property
    def members_list(self):
        return [m.user for m in self.members]  # ty:ignore[not-iterable]


class GroupMember(db.Model):  # ty:ignore[unsupported-base]
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    role = db.Column(
        db.String(50), default="member", nullable=False
    )  # owner, admin, member, moderator, editor
    created_at = db.Column(
        db.DateTime, default=datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint("group_id", "user_id", name="uq_group_member"),
    )

    def __repr__(self) -> str:
        return f"<GroupMember {self.user_id} in {self.group_id}>"


class GroupResource(db.Model):  # ty:ignore[unsupported-base]
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    resource_type = db.Column(db.String(64), nullable=False)  # e.g., hive_account
    resource_id = db.Column(db.String(64), nullable=False)  # e.g., username
    created_at = db.Column(
        db.DateTime, default=datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint(
            "group_id", "resource_type", "resource_id", name="uq_group_resource_link"
        ),
    )

    def __repr__(self) -> str:
        return f"<GroupResource {self.resource_type}:{self.resource_id} for {self.group_id}>"


class Draft(db.Model):  # ty:ignore[unsupported-base]
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    author_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # The shared hive account this will be posted FROM
    hive_account_username = db.Column(db.String(16), nullable=True)

    title = db.Column(db.String(256), nullable=False)
    body = db.Column(db.Text, nullable=False)
    tags = db.Column(db.String(256))  # Space separated
    permlink = db.Column(db.String(256), nullable=False)
    beneficiaries = db.Column(
        db.Text
    )  # JSON string: [{"account": "user", "weight": 1000}]

    status = db.Column(db.String(20), default="draft")  # draft, published
    tx_id = db.Column(db.String(64))

    created_at = db.Column(
        db.DateTime, default=datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )
    published_at = db.Column(db.DateTime)

    def __repr__(self) -> str:
        return f"<Draft {self.title} by {self.author_user_id}>"


@login_manager.user_loader
def load_user(id):
    return db.session.get(User, int(id))


class DraftVersion(Document):
    draft_id = IntField(required=True)  # Link to SQL Draft.id
    version_number = IntField(required=True)
    title = StringField(required=True)
    body = StringField(required=True)
    tags = StringField()  # Stores space-separated tags
    # beneficiaries not strictly needed if we enforce system fee logic, but good for history
    saved_at = DateTimeField(required=True, default=datetime.now(timezone.utc))
    saved_by_user_id = IntField(required=True)

    meta = {"collection": "draft_versions"}  # Specify collection name


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255))
    type = db.Column(db.String(50), default="info")
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Notification {self.id} for {self.user_id}>"
