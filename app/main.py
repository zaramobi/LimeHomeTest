from http import HTTPStatus

from fastapi import FastAPI, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .crud import UnableToBook
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def hello_world():
    return {"message": "OK"}


@app.post("/api/v1/booking", response_model=schemas.BookingBase)
def create_booking(booking: schemas.BookingBase, db: Session = Depends(get_db)):
    try:
        return crud.create_booking(db=db, booking=booking)
    except UnableToBook as unable_to_book:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST,
                            detail=str(unable_to_book))

@app.get("/api/v1/booking/{booking_id}", response_model=schemas.BookingBase)
def read_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = crud.get_booking_by_id(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

@app.patch("/api/v1/booking/extend", response_model=schemas.BookingBase)
def extend_booking(payload: schemas.BookingExtension, db: Session = Depends(get_db)):
    try:
        return crud.extend_booking(db=db, booking_id=payload.booking_id, extension_days=payload.extension_days)
    except UnableToBook as unable_to_book:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(unable_to_book),
        )