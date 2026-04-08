"""
Economy API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.core.database import db
from src.services.economy import EconomyService
from src.core.exceptions import InsufficientBalanceException

router = APIRouter(prefix="/economy", tags=["economy"])

class RedeemRequest(BaseModel):
    user_id: int
    amount: int
    description: str

class TransferRequest(BaseModel):
    from_user_id: int
    to_user_id: int
    amount: int

class BalanceResponse(BaseModel):
    user_id: int
    balance: int

async def get_economy_service():
    async with db.session() as session:
        yield EconomyService(session)

@router.get("/balance/{user_id}", response_model=BalanceResponse)
async def get_balance(
    user_id: int,
    service: EconomyService = Depends(get_economy_service)
):
    balance = await service.get_balance(user_id)
    return BalanceResponse(user_id=user_id, balance=balance)

@router.post("/redeem")
async def redeem_reward(
    request: RedeemRequest,
    service: EconomyService = Depends(get_economy_service)
):
    try:
        # Check balance first
        balance = await service.get_balance(request.user_id)
        if balance < request.amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")

        # Process redemption (Debit)
        transaction = await service.process_transaction(
            user_id=request.user_id,
            amount=request.amount,
            type="debit",
            category="redemption",
            description=request.description,
            reference_id=f"redeem_{request.user_id}_{request.amount}_{request.description}" # Ideally UUID from client
        )
        
        # Fetch updated balance
        new_balance = await service.get_balance(request.user_id)
        
        return {"status": "success", "transaction_id": transaction.id, "new_balance": new_balance}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transfer")
async def transfer_tokens(
    request: TransferRequest,
    service: EconomyService = Depends(get_economy_service)
):
    try:
        sender_bal, recipient_bal = await service.transfer_tokens(
            request.from_user_id,
            request.to_user_id,
            request.amount
        )
        return {
            "status": "success",
            "sender_balance": sender_bal,
            "recipient_balance": recipient_bal
        }
    except InsufficientBalanceException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
