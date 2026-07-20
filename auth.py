import mysql.connector
from passlib.context import CryptContext
from database import Database

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthManager:
    """Handles user registration and login. Passwords are hashed with
    bcrypt before being stored — never stored or compared as plaintext."""

    def __init__(self, db: Database):
        self.db = db

    def register_user(self, username, password):
        """Registers a new user. Returns the new user_id, or None if the username is taken."""
        hashed_password = pwd_context.hash(password)
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, hashed_password)
            )
            conn.commit()
            return cursor.lastrowid
        except mysql.connector.Error:
            return None
        finally:
            conn.close()

    def login_user(self, username, password):
        """Returns the user_id if credentials are valid, otherwise None."""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, password FROM users WHERE username=%s",
                (username,)
            )
            result = cursor.fetchone()
            if not result:
                return None
            user_id, hashed_password = result
            if pwd_context.verify(password, hashed_password):
                return user_id
            return None
        finally:
            conn.close()
