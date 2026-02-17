"""Subscription models for the notification engine."""

from pydantic import BaseModel, Field

from .events import CAOEventType


class CAOSubscription(BaseModel):
    """Subscription to events for a specific CAO."""

    cao_naam: str
    event_types: list[CAOEventType] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list, description="email, webhook, etc.")
    lead_time_days: int = Field(14, description="Days before moment to send notification")
    webhook_url: str | None = None


class Subscriber(BaseModel):
    """A subscriber to CAO change notifications."""

    subscriber_id: str
    subscriber_name: str
    email: str | None = None
    cao_subscriptions: list[CAOSubscription] = Field(default_factory=list)
    global_event_types: list[CAOEventType] = Field(
        default_factory=list, description="Event types to receive for ALL CAOs"
    )
    active: bool = True
