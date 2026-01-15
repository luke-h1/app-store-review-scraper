from dataclasses import dataclass
from datetime import datetime


@dataclass
class Review:
    """Normalized review data structure."""

    id: str
    store: str
    app_name: str
    user_name: str
    rating: int
    title: str | None
    content: str
    date: datetime
    app_id: str | None = None

    def to_dict(self) -> dict:
        """Convert review to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "store": self.store,
            "app_name": self.app_name,
            "app_id": self.app_id,
            "user_name": self.user_name,
            "rating": self.rating,
            "title": self.title,
            "content": self.content,
            "date": self.date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Review":
        """Create review from dictionary."""
        return cls(
            id=data["id"],
            store=data["store"],
            app_name=data["app_name"],
            app_id=data.get("app_id"),
            user_name=data["user_name"],
            rating=data["rating"],
            title=data.get("title"),
            content=data["content"],
            date=datetime.fromisoformat(data["date"]),
        )
