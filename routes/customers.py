from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Customer, Order
from schemas import CustomerCreate, CustomerResponse, OrderResponse


router = APIRouter(
    prefix="/customers",
    tags=["customers"]
)


@router.post("", response_model=CustomerResponse)
def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db)
):
    existing_customer = db.query(Customer).filter(
        Customer.email == customer_data.email
    ).first()

    if existing_customer is not None:
        raise HTTPException(
            status_code=400,
            detail="Customer with this email already exists"
        )

    customer = Customer(
        name=customer_data.name,
        email=customer_data.email,
        phone=customer_data.phone
    )

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return customer


@router.get("", response_model=list[CustomerResponse])
def get_customers(db: Session = Depends(get_db)):
    customers = db.query(Customer).all()
    return customers


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int,
    customer_data: CustomerCreate,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    customer.name = customer_data.name
    customer.email = customer_data.email
    customer.phone = customer_data.phone

    db.commit()
    db.refresh(customer)

    return customer


@router.delete("/{customer_id}")
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    db.delete(customer)
    db.commit()

    return ({"message": "Customer deleted successfully"}


@router.get("/{customer_id}/orders", response_model=list[OrderResponse]))
def get_customer_orders(
    customer_id: int,
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    orders = db.query(Order).filter(Order.customer_id == customer_id).all()

    return orders

