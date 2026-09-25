from datetime import date as Date
from typing import Annotated, Optional, Literal
from fastapi import FastAPI, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
import models
from models import Transaction
from database import engine, get_db
from router import auth
from router.auth import get_current_user

app = FastAPI(title="Personal Expense Tracker API", version="1.0.0")
models.Base.metadata.create_all(bind=engine)
app.include_router(auth.router)

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

class TransactionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    amount: float = Field(gt=0)
    type: Literal["income", "expense"]
    category: str = Field(min_length=1, max_length=100)
    date: Date

class TransactionUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=150)
    amount: Optional[float] = Field(default=None, gt=0)
    type: Optional[Literal["income", "expense"]] = None
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    date: Optional[Date] = None

class TransactionResponse(BaseModel):
    id: int
    title: str
    amount: float
    type: Literal["income", "expense"]
    category: str
    date: Date
    owner_id: int
    model_config = ConfigDict(from_attributes=True)

@app.get("/transactions", response_model=list[TransactionResponse])
def get_transactions(user: user_dependency, db: db_dependency):
    return db.query(Transaction).filter(Transaction.owner_id == user["id"]).all()

@app.get("/transactions/filter", response_model=list[TransactionResponse])
def filter_transactions(
    user: user_dependency,
    db: db_dependency,
    type: Optional[Literal["income", "expense"]] = Query(default=None),
    category: Optional[str] = Query(default=None),
    minimum_amount: Optional[float] = Query(default=None, ge=0),
    maximum_amount: Optional[float] = Query(default=None, ge=0)
):
    if minimum_amount is not None and maximum_amount is not None and minimum_amount > maximum_amount:
        raise HTTPException(status_code=400, detail="Minimum amount cannot be greater than maximum amount")
    query = db.query(Transaction).filter(Transaction.owner_id == user["id"])
    if type is not None:
        query = query.filter(Transaction.type == type)
    if category is not None:
        query = query.filter(Transaction.category == category)
    if minimum_amount is not None:
        query = query.filter(Transaction.amount >= minimum_amount)
    if maximum_amount is not None:
        query = query.filter(Transaction.amount <= maximum_amount)
    return query.all()

@app.get("/transactions/{transaction_id}", response_model=TransactionResponse)
def get_specific_transaction(transaction_id: int, user: user_dependency, db: db_dependency):
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.owner_id == user["id"]
    ).first()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction

@app.post("/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(new_transaction: TransactionCreate, user: user_dependency, db: db_dependency):
    transaction_model = Transaction(**new_transaction.model_dump(), owner_id=user["id"])
    db.add(transaction_model)
    db.commit()
    db.refresh(transaction_model)
    return transaction_model

@app.put("/transactions/{transaction_id}", response_model=TransactionResponse)
def update_transaction(transaction_id: int, update_data: TransactionUpdate, user: user_dependency, db: db_dependency):
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.owner_id == user["id"]
    ).first()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(transaction, key, value)
    db.commit()
    db.refresh(transaction)
    return transaction

@app.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: int, user: user_dependency, db: db_dependency):
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.owner_id == user["id"]
    ).first()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(transaction)
    db.commit()
    return {"message": "Transaction deleted successfully"}
