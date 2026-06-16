from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Customer, Order, User
from schemas import CustomerCreate, CustomerResponse, OrderResponse
from routes.auth import get_current_user, get_admin_user

router = APIRouter(
    prefix="/customers",
    tags=["customers"]
)


def ensure_customer_access(customer: Customer, current_user: User) -> None:
    if current_user.role == "admin":
        return

    if customer.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")


@router.post("", response_model=CustomerResponse)
def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing_customer = db.query(Customer).filter(
        Customer.user_id == current_user.id
    ).first()

    if existing_customer is not None:
        raise HTTPException(
            status_code=400,
            detail="Customer profile already exists for this user"
        )

    customer = Customer(
        user_id=current_user.id,
        name=customer_data.name,
        email=customer_data.email,
        phone=customer_data.phone
    )

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return customer


@router.get("", response_model=list[CustomerResponse])
def get_customers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    customers = db.query(Customer).all()
    return customers


@router.get("/me", response_model=CustomerResponse)
def get_my_customer_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    customer = db.query(Customer).filter(
        Customer.user_id == current_user.id
    ).first()

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer profile not found"
        )

    return customer


@router.put("/me", response_model=CustomerResponse)
def update_my_customer_profile(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    customer = db.query(Customer).filter(
        Customer.user_id == current_user.id
    ).first()

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer profile not found"
        )

    email_owner = db.query(Customer).filter(
        Customer.email == customer_data.email,
        Customer.id != customer.id
    ).first()

    if email_owner is not None:
        raise HTTPException(
            status_code=409,
            detail="Customer email already exists"
        )

    customer.name = customer_data.name
    customer.email = customer_data.email
    customer.phone = customer_data.phone

    db.commit()
    db.refresh(customer)

    return customer


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    ensure_customer_access(customer, current_user)

    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int,
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    ensure_customer_access(customer, current_user)

    customer.name = customer_data.name
    customer.email = customer_data.email
    customer.phone = customer_data.phone

    db.commit()
    db.refresh(customer)

    return customer


@router.delete("/{customer_id}")
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    existing_order = db.query(Order).filter(
        Order.customer_id == customer_id
    ).first()

    if existing_order is not None:
        raise HTTPException(
            status_code=409,
            detail="Customer cannot be deleted because they have orders"
        )

    db.delete(customer)
    db.commit()

    return {"message": "Customer deleted successfully"}


@router.get("/{customer_id}/orders", response_model=list[OrderResponse])
def get_customer_orders(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    orders = db.query(Order).filter(Order.customer_id == customer_id).all()

    return orders
