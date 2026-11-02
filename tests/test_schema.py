from src.models import Base


def test_expected_tables_exist():
    assert set(Base.metadata.tables) == {
        "slots",
        "bookings",
        "idempotency_keys",
        "booking_attempts",
        "rate_limit_locks",
    }


def test_booking_unique_partial_index_exists():
    booking = Base.metadata.tables["bookings"]
    unique_indexes = [index for index in booking.indexes if index.unique]
    assert any(
        index.name == "uq_one_confirmed_booking_per_slot"
        and str(index.dialect_options["postgresql"]["where"]) == "status = 'confirmed'"
        for index in unique_indexes
    )
