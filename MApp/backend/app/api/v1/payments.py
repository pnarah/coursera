"""
Payment endpoints.
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.hotel import User
from app.schemas.payment import PaymentCreate, PaymentResponse, PaymentDetail, WebhookPayload
from app.services.payment_service import PaymentService

router = APIRouter()


@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment_data: PaymentCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """
    Create a payment for a booking.
    
    This initiates a payment with the payment gateway (Stripe/Razorpay).
    Returns a client_secret for completing the payment on the client side.
    """
    try:
        payment = await PaymentService.create_payment(
            db=db,
            booking_id=payment_data.booking_id,
            user_id=current_user["user_id"],
            amount=payment_data.amount,
            currency=payment_data.currency,
            return_url=payment_data.return_url
        )
        return payment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment: {str(e)}"
        )


@router.get("/{payment_id}", response_model=PaymentDetail)
async def get_payment(
    payment_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """Get payment details."""
    payment = await PaymentService.get_payment_by_id(db, payment_id, current_user["user_id"])
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    return payment


@router.post("/webhooks/payment", status_code=status.HTTP_200_OK)
async def payment_webhook(
    payload: WebhookPayload,
    db: AsyncSession = Depends(get_db),
    x_webhook_signature: str = Header(None, alias="x-webhook-signature")
):
    """
    Handle payment webhook from payment gateway.
    
    In production, this should:
    1. Verify webhook signature
    2. Handle idempotency
    3. Process different event types
    
    For this mock implementation, we'll handle success/failure events.
    """
    try:
        # In production: Verify signature with stripe.Webhook.construct_event()
        # For mock, we'll skip verification
        
        if payload.event_type == "payment_intent.succeeded":
            # Extract payment details from payload
            payment_id = int(payload.data.get("payment_id", 0))
            gateway_payment_id = payload.payment_id
            payment_method = payload.data.get("payment_method")
            
            if payment_id and gateway_payment_id:
                await PaymentService.confirm_payment(
                    db=db,
                    payment_id=payment_id,
                    gateway_payment_id=gateway_payment_id,
                    payment_method=payment_method
                )
        
        elif payload.event_type == "payment_intent.failed":
            payment_id = int(payload.data.get("payment_id", 0))
            failure_reason = payload.data.get("failure_reason", "Payment failed")
            
            if payment_id:
                await PaymentService.fail_payment(
                    db=db,
                    payment_id=payment_id,
                    failure_reason=failure_reason
                )
        
        return {"status": "success"}
    
    except Exception as e:
        # In production, log the error but still return 200 to avoid webhook retries
        # For now, we'll return error status
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )
