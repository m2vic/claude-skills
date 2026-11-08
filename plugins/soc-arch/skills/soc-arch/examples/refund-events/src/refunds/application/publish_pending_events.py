from refunds.application.ports import Database, EventPublisher


def publish_pending_events(db: Database, publisher: EventPublisher, limit: int = 100) -> int:
    """Outbox relay. A crash between the two calls republishes, so delivery is at-least-once."""
    events = db.pending_events(limit)
    for event in events:
        publisher.publish(event)
        db.mark_published(event.event_id)
    return len(events)
