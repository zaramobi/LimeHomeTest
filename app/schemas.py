import datetime

from pydantic import BaseModel


class BookingBase(BaseModel):
    guest_name: str
    unit_id: str
    check_in_date: datetime.date
    number_of_nights: int

    class Config:
        orm_mode = True
    
class BookingExtension(BaseModel):
    booking_id: int
    extension_days: int