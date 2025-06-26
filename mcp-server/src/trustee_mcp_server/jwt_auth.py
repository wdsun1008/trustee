"""JWT authentication module for KBS operations."""

import time
from pathlib import Path
from typing import Optional

import jwt
import structlog
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

logger = structlog.get_logger()


class JWTAuthenticator:
    """JWT token authenticator for KBS operations."""

    def __init__(self, private_key_path: Optional[str] = None):
        """Initialize JWT authenticator."""
        self.private_key_path = private_key_path
        self._private_key: Optional[ed25519.Ed25519PrivateKey] = None

        if private_key_path:
            self._load_private_key()

    def _load_private_key(self) -> None:
        """Load ED25519 private key from file."""
        if not self.private_key_path:
            return

        try:
            key_path = Path(self.private_key_path)
            if not key_path.exists():
                logger.warning("Private key file not found", path=self.private_key_path)
                return

            with open(key_path, "rb") as key_file:
                key_data = key_file.read()

            # Load the private key
            loaded_key = serialization.load_pem_private_key(
                key_data,
                password=None,
            )

            # Verify it's an ED25519 key
            if not isinstance(loaded_key, ed25519.Ed25519PrivateKey):
                logger.error("Private key is not ED25519 format")
                self._private_key = None
                return

            self._private_key = loaded_key

            logger.info("Successfully loaded ED25519 private key for JWT authentication")

        except Exception as e:
            logger.error("Failed to load private key", error=str(e), path=self.private_key_path)
            self._private_key = None

    def is_configured(self) -> bool:
        """Check if JWT authentication is properly configured."""
        return self._private_key is not None

    def create_auth_token(self) -> str:
        """Create JWT authentication token."""
        if not self._private_key:
            raise ValueError("JWT authentication not configured - private key not loaded")

        # Create JWT payload
        now = int(time.time())
        payload = {
            "iat": now,  # Issued at
            "exp": now + 7200,  # Expires in 2 hours (7200 seconds)
        }

        try:
            # Sign the JWT token using ED25519
            token = jwt.encode(payload, self._private_key, algorithm="EdDSA")

            logger.debug("Created JWT auth token", expires_at=payload["exp"])
            return token

        except Exception as e:
            logger.error("Failed to create JWT token", error=str(e))
            raise ValueError(f"Failed to create JWT token: {e}")

    def verify_token(self, token: str) -> dict:
        """Verify JWT token (for testing purposes)."""
        if not self._private_key:
            raise ValueError("JWT authentication not configured")

        try:
            # Get the public key from private key for verification
            public_key = self._private_key.public_key()

            # Verify and decode the token
            payload = jwt.decode(token, public_key, algorithms=["EdDSA"])

            return payload

        except jwt.ExpiredSignatureError:
            raise ValueError("JWT token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid JWT token: {e}")
