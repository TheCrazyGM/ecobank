from app import create_app, db
from app.models import User

app = create_app()


def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="admin").first():
            print("Creating admin user...")
            admin = User(username="admin", email="admin@example.com")
            admin.set_password("password")
            db.session.add(admin)
            db.session.commit()
            print("Admin user created.")


if __name__ == "__main__":
    init_db()
