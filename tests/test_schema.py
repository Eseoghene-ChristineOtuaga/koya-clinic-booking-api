from src.models import Base


def test_expected_tables_exist():
    assert set(Base.metadata.tables) == {
        "koya_clinic.slots",
        "koya_clinic.bookings",
        "koya_clinic.idempotency_keys",
        "koya_clinic.booking_attempts",
        "koya_clinic.rate_limit_locks",
    }


def test_booking_unique_partial_index_exists():
    booking = Base.metadata.tables["koya_clinic.bookings"]
    unique_indexes = [index for index in booking.indexes if index.unique]
    assert any(
        index.name == "uq_one_confirmed_booking_per_slot"
        and str(index.dialect_options["postgresql"]["where"]) == "status = 'confirmed'"
        for index in unique_indexes
    )


def test_all_tables_are_isolated_in_clinic_schema():
    assert all(table.schema == "koya_clinic" for table in Base.metadata.tables.values())


def test_booking_fk_points_to_clinic_schema():
    booking = Base.metadata.tables["koya_clinic.bookings"]
    fk = next(iter(booking.c.slot_id.foreign_keys))
    assert fk.target_fullname == "koya_clinic.slots.id"
