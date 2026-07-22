from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Crypto:
    """
    Cryptographic and password security utilities.
    """

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a plaintext password securely using bcrypt.

        Args:
            password (str): Plaintext password.

        Returns:
            str: Hashed password string.
        """
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plaintext password against a hashed password.

        Args:
            plain_password (str): Plaintext input password.
            hashed_password (str): Hashed password from database.

        Returns:
            bool: True if password matches, False otherwise.
        """
        return pwd_context.verify(plain_password, hashed_password)
