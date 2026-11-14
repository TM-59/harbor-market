from django.db import models


class TradingSessionRecord(models.Model):
    session_id: models.CharField[str, str] = models.CharField(max_length=64, primary_key=True)
    day: models.PositiveSmallIntegerField[int, int] = models.PositiveSmallIntegerField()
    coins: models.PositiveIntegerField[int, int] = models.PositiveIntegerField()
    grain: models.PositiveSmallIntegerField[int, int] = models.PositiveSmallIntegerField()
    salt: models.PositiveSmallIntegerField[int, int] = models.PositiveSmallIntegerField()
    settled: models.BooleanField[bool, bool] = models.BooleanField()
    revision: models.PositiveBigIntegerField[int, int] = models.PositiveBigIntegerField(default=0)

    class Meta:
        db_table = "harbor_market_session"


class SessionEventRecord(models.Model):
    session: models.ForeignKey[TradingSessionRecord, TradingSessionRecord] = models.ForeignKey(
        TradingSessionRecord, on_delete=models.CASCADE, related_name="event_records"
    )
    sequence: models.PositiveBigIntegerField[int, int] = models.PositiveBigIntegerField()
    event_type: models.CharField[str, str] = models.CharField(max_length=32)
    payload = models.JSONField()

    class Meta:
        db_table = "harbor_market_session_event"
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "sequence"], name="harbor_market_unique_event_sequence"
            )
        ]
