import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.models.user import User


@pytest.mark.requires_db
class TestUserModel:
    """Test cases for User model functionality."""

    def test_user_creation(self, test_db_session):
        """Test basic user creation with required fields."""
        user = User(
            email="test@example.com",
            hashed_password="hashed_password_123",
            full_name="Test User"
        )
        test_db_session.add(user)
        test_db_session.commit()

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.hashed_password == "hashed_password_123"
        assert user.full_name == "Test User"
        assert user.is_active is True  # Default value
        assert user.is_superuser is False  # Default value
        assert isinstance(user.created_at, datetime)
        assert user.last_login is None

    def test_user_creation_minimal_fields(self, test_db_session):
        """Test user creation with only required fields."""
        user = User(
            email="minimal@example.com",
            hashed_password="hashed_password_456"
        )
        test_db_session.add(user)
        test_db_session.commit()

        assert user.id is not None
        assert user.email == "minimal@example.com"
        assert user.hashed_password == "hashed_password_456"
        assert user.full_name is None
        assert user.is_active is True
        assert user.is_superuser is False

    def test_user_email_unique_constraint(self, test_db_session):
        """Test that email uniqueness is enforced."""
        user1 = User(
            email="duplicate@example.com",
            hashed_password="password1"
        )
        user2 = User(
            email="duplicate@example.com",
            hashed_password="password2"
        )

        test_db_session.add(user1)
        test_db_session.commit()

        test_db_session.add(user2)
        with pytest.raises(IntegrityError):
            test_db_session.commit()

    def test_user_superuser_creation(self, test_db_session):
        """Test creation of superuser."""
        user = User(
            email="admin@example.com",
            hashed_password="admin_password",
            full_name="Admin User",
            is_superuser=True
        )
        test_db_session.add(user)
        test_db_session.commit()

        assert user.is_superuser is True
        assert user.is_active is True

    def test_user_inactive_user(self, test_db_session):
        """Test creation of inactive user."""
        user = User(
            email="inactive@example.com",
            hashed_password="inactive_password",
            is_active=False
        )
        test_db_session.add(user)
        test_db_session.commit()

        assert user.is_active is False
        assert user.is_superuser is False

    def test_user_last_login_update(self, test_db_session):
        """Test updating last_login timestamp."""
        user = User(
            email="login@example.com",
            hashed_password="login_password"
        )
        test_db_session.add(user)
        test_db_session.commit()

        assert user.last_login is None

        # Update last_login
        login_time = datetime.utcnow()
        user.last_login = login_time
        test_db_session.commit()

        assert user.last_login == login_time

    def test_user_repr(self, test_db_session):
        """Test User string representation."""
        user = User(
            email="repr@example.com",
            hashed_password="repr_password",
            is_active=True
        )
        test_db_session.add(user)
        test_db_session.commit()

        repr_str = repr(user)
        assert "User(" in repr_str
        assert f"id={user.id}" in repr_str
        assert "email='repr@example.com'" in repr_str
        assert "active=True" in repr_str

    def test_user_long_email(self, test_db_session):
        """Test user with email near the length limit."""
        # Email field is String(255), so test with a long but valid email
        long_email = "a" * 240 + "@example.com"  # 252 characters total
        user = User(
            email=long_email,
            hashed_password="long_email_password"
        )
        test_db_session.add(user)
        test_db_session.commit()

        assert user.email == long_email

    def test_user_long_full_name(self, test_db_session):
        """Test user with full name near the length limit."""
        # full_name field is String(255)
        long_name = "A" * 255
        user = User(
            email="longname@example.com",
            hashed_password="long_name_password",
            full_name=long_name
        )
        test_db_session.add(user)
        test_db_session.commit()

        assert user.full_name == long_name

    def test_user_query_by_email(self, test_db_session):
        """Test querying user by email."""
        user = User(
            email="query@example.com",
            hashed_password="query_password"
        )
        test_db_session.add(user)
        test_db_session.commit()

        queried_user = test_db_session.query(User).filter(User.email == "query@example.com").first()
        assert queried_user is not None
        assert queried_user.id == user.id
        assert queried_user.email == "query@example.com"

    def test_user_filter_active_users(self, test_db_session):
        """Test filtering active vs inactive users."""
        active_user = User(
            email="active@example.com",
            hashed_password="active_password",
            is_active=True
        )
        inactive_user = User(
            email="inactive@example.com",
            hashed_password="inactive_password",
            is_active=False
        )

        test_db_session.add_all([active_user, inactive_user])
        test_db_session.commit()

        active_users = test_db_session.query(User).filter(User.is_active == True).all()
        inactive_users = test_db_session.query(User).filter(User.is_active == False).all()

        assert len(active_users) >= 1
        assert len(inactive_users) >= 1
        assert active_user in active_users
        assert inactive_user in inactive_users