"""API Key models for customer authentication."""

import hashlib
import secrets
from datetime import datetime

from pydantic import BaseModel, Field


class APIKey(BaseModel):
    """API Key model for customer authentication."""

    id: str = Field(description="Unique identifier")
    customer_id: str = Field(description="Customer ID")
    name: str = Field(description="Key name/description")
    key_hash: str = Field(description="Hashed API key")
    key_prefix: str = Field(description="Key prefix for identification")
    created_at: datetime = Field(default_factory=datetime.now)
    last_used: datetime | None = None
    is_active: bool = True

    # Usage limits
    monthly_limit: int = Field(default=50000, description="Monthly API call limit")
    calls_this_month: int = Field(default=0)

    # Permissions
    scopes: list[str] = Field(default_factory=lambda: ["read:cao", "validate:payroll"])

    @classmethod
    def create_new(cls, customer_id: str, name: str, monthly_limit: int = 50000) -> tuple["APIKey", str]:
        """Create a new API key and return both the model and the raw key."""
        raw_key = f"cao_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:8]

        api_key = cls(
            id=secrets.token_urlsafe(16),
            customer_id=customer_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            monthly_limit=monthly_limit
        )

        return api_key, raw_key

    def verify_key(self, raw_key: str) -> bool:
        """Verify if a raw key matches this API key."""
        return hashlib.sha256(raw_key.encode()).hexdigest() == self.key_hash

    def can_make_request(self) -> bool:
        """Check if this key can make more requests."""
        return self.is_active and self.calls_this_month < self.monthly_limit


class Customer(BaseModel):
    """Customer model for B2B users."""

    id: str = Field(description="Unique identifier")
    company_name: str
    email: str
    created_at: datetime = Field(default_factory=datetime.now)

    # Subscription
    plan: str = Field(default="starter", description="starter|growth|enterprise")
    monthly_limit: int = Field(default=10000)

    # Billing
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None

    # Contact
    contact_name: str | None = None
    phone: str | None = None

    # Features
    webhook_enabled: bool = False
    bulk_validation_enabled: bool = False