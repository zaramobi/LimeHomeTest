import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.main import app, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

GUEST_A_UNIT_1: dict = {
    'unit_id': '1', 'guest_name': 'GuestA', 'check_in_date': datetime.date.today().strftime('%Y-%m-%d'),
    'number_of_nights': 5
}
GUEST_A_UNIT_2: dict = {
    'unit_id': '2', 'guest_name': 'GuestA', 'check_in_date': datetime.date.today().strftime('%Y-%m-%d'),
    'number_of_nights': 5
}
GUEST_B_UNIT_1: dict = {
    'unit_id': '1', 'guest_name': 'GuestB', 'check_in_date': datetime.date.today().strftime('%Y-%m-%d'),
    'number_of_nights': 5
}
GUEST_B_UNIT_1_TOMORROW: dict = {
    'unit_id': '1', 'guest_name': 'GuestB', 'check_in_date': (datetime.date.today() + datetime.timedelta(1)).strftime('%Y-%m-%d'),
    'number_of_nights': 5
}
GUEST_B_UNIT_1_NEXT_WEEK: dict = {
    'unit_id': '1', 'guest_name': 'GuestB', 'check_in_date': (datetime.date.today() + datetime.timedelta(7)).strftime('%Y-%m-%d'),
    'number_of_nights': 5
}

@pytest.fixture()
def test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.mark.freeze_time('2023-05-21')
def test_create_fresh_booking(test_db):
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    response.raise_for_status()
    assert response.status_code == 200, response.text


@pytest.mark.freeze_time('2023-05-21')
def test_same_guest_same_unit_booking(test_db):
    # Create first booking
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    assert response.status_code == 200, response.text
    response.raise_for_status()

    # Guests want to book same unit again
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    assert response.status_code == 400, response.text
    assert response.json()['detail'] == 'The given guest name cannot book the same unit multiple times'


@pytest.mark.freeze_time('2023-05-21')
def test_same_guest_different_unit_booking(test_db):
    # Create first booking
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    assert response.status_code == 200, response.text

    # Guest wants to book another unit
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_2
    )
    assert response.status_code == 400, response.text
    assert response.json()['detail'] == 'The same guest cannot be in multiple units at the same time'


@pytest.mark.freeze_time('2023-05-21')
def test_different_guest_same_unit_booking(test_db):
    # Create first booking
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    assert response.status_code == 200, response.text

    # GuestB trying to book a unit that is already occuppied
    response = client.post(
        "/api/v1/booking",
        json=GUEST_B_UNIT_1
    )
    assert response.status_code == 400, response.text
    assert response.json()['detail'] == 'For the given date range, the unit is already occupied'


@pytest.mark.freeze_time('2023-05-21')
def test_different_guest_same_unit_booking_different_date(test_db):
    # Create first booking
    response = client.post(
        "/api/v1/booking",
        json=GUEST_A_UNIT_1
    )
    assert response.status_code == 200, response.text

    # GuestB trying to book a unit that is already occuppied

    response = client.post(
        "/api/v1/booking",
        json=GUEST_B_UNIT_1_TOMORROW
    )

    assert response.status_code == 400, response.text
    assert response.json()['detail'] == 'For the given date range, the unit is already occupied'


# run test for new feature (extend)
@pytest.mark.freeze_time('2025-06-01')
def test_extend_booking_success(test_db):
    # Create initial booking first
    response = client.post("/api/v1/booking", json=GUEST_A_UNIT_1)
    assert response.status_code == 200
    booking = response.json()
    
    # Prepare extension payload
    payload = {
        "booking_id": 1,
        "extension_days": 2
    }
    
    response = client.patch("/api/v1/booking/extend", json=payload)
    assert response.status_code == 200
    extended_booking = response.json()
    assert extended_booking['number_of_nights'] == GUEST_A_UNIT_1['number_of_nights'] + 2

@pytest.mark.freeze_time('2025-06-01')
def test_extend_booking_fail_overlap(test_db):
    # Create booking for GuestA unit 1
    response = client.post("/api/v1/booking", json=GUEST_A_UNIT_1)
    assert response.status_code == 200
    booking_a = response.json()

    # Create booking for GuestB starting after GuestA
    response = client.post("/api/v1/booking", json=GUEST_B_UNIT_1_NEXT_WEEK)
    assert response.status_code == 200

    # Try to extend GuestA's booking by 1 day (should overlap)
    payload = {
        "booking_id": 1,
        "extension_days": 3
    }
    response = client.patch("/api/v1/booking/extend", json=payload)
    assert response.status_code == 400
    assert "unit is not available" in response.json()['detail'].lower()

def test_extend_nonexistent_booking(test_db):
    payload = {
        "booking_id": 999999,
        "extension_days": 2
    }
    response = client.patch("/api/v1/booking/extend", json=payload)
    assert response.status_code == 400 or response.status_code == 404