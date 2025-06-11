from typing import Tuple

from sqlalchemy.orm import Session

from . import models, schemas

from sqlalchemy import func
from typing import Optional

class UnableToBook(Exception):
    pass


def create_booking(db: Session, booking: schemas.BookingBase) -> models.Booking:
    (is_possible, reason) = is_booking_possible(db=db, booking=booking)
    if not is_possible:
        raise UnableToBook(reason)
    db_booking = models.Booking(
        guest_name=booking.guest_name, unit_id=booking.unit_id,
        check_in_date=booking.check_in_date, number_of_nights=booking.number_of_nights)
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking

def is_overlapped_booking(db: Session, booking: schemas.BookingBase, exclude_booking_id: Optional[int] = None) -> bool:
    try:
        query = db.query(models.Booking).filter(
            models.Booking.unit_id == booking.unit_id,
            func.julianday(booking.check_in_date) - func.julianday(models.Booking.check_in_date) < models.Booking.number_of_nights,
            func.julianday(models.Booking.check_in_date) - func.julianday(booking.check_in_date) < booking.number_of_nights,
        )
        if exclude_booking_id is not None:
            query = query.filter(models.Booking.id != exclude_booking_id)
        
        overlapping_booking = query.first()
        return overlapping_booking is not None
    except Exception:
        return False

def is_booking_possible(db: Session, booking: schemas.BookingBase) -> Tuple[bool, str]:
    # check 1 : The Same guest cannot book the same unit multiple times
    is_same_guest_booking_same_unit = db.query(models.Booking) \
        .filter_by(guest_name=booking.guest_name, unit_id=booking.unit_id).first()

    if is_same_guest_booking_same_unit:
        return False, 'The given guest name cannot book the same unit multiple times'

    # check 2 : the same guest cannot be in multiple units at the same time
    is_same_guest_already_booked = db.query(models.Booking) \
        .filter_by(guest_name=booking.guest_name).first()
    if is_same_guest_already_booked:
        return False, 'The same guest cannot be in multiple units at the same time'

    # check 3 : Unit is available for the check-in date
    # Query for overlapping bookings
    overlapping_booking = is_overlapped_booking(db, booking)

    if overlapping_booking:
        return False, 'For the given date range, the unit is already occupied'

    return True, 'OK'

def get_booking_by_id(db: Session, booking_id: int) ->  Optional[models.Booking]:
    return db.query(models.Booking).filter(models.Booking.id == booking_id).first()

def extend_booking(db: Session, booking_id: int, extension_days: int) -> models.Booking:
    # Fetch the existing booking
    booking = get_booking_by_id(db, booking_id)
    if not booking:
        raise UnableToBook(f"Booking with ID {booking_id} does not exist.")
    booking.number_of_nights += extension_days
    # Validate no overlapping bookings for the same unit
    overlapping_booking = is_overlapped_booking(db, booking, booking_id)

    if overlapping_booking:
        raise UnableToBook("The unit is not available for the requested extension.")

    # Update the booking with the new number of nights
    db.commit()
    db.refresh(booking)
    return booking

