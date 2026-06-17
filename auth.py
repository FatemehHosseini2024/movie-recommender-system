import mysql.connector
from database import Database


class AuthManager:
    """Handles user registration and login."""

    def __init__(self, db: Database):
        self.db = db

    def register_user(self, username, password):
        """Registers a new user. Returns the new user_id, or None if the username is taken."""
        cursor = self.db.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, password)
            )
            self.db.conn.commit()
            return cursor.lastrowid
        except mysql.connector.Error:
            return None

    def login_user(self, username, password):
        """Returns the user_id if credentials are valid, otherwise None."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT user_id FROM users WHERE username=%s AND password=%s",
            (username, password)
        )
        result = cursor.fetchone()
        return result[0] if result else None
