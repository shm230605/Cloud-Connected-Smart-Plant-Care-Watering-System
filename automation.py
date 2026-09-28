from datetime import datetime, timedelta, timezone

COOLDOWN = timedelta(seconds=45)


def should_water(soil: float, threshold: float, tank: float, auto_water: bool, last_watered: str | None) -> bool:
    if not auto_water or soil >= threshold or tank <= 10:
        return False
    if not last_watered:
        return True
    try:
        previous = datetime.fromisoformat(last_watered)
        return datetime.now(timezone.utc) - previous >= COOLDOWN
    except ValueError:
        return True
