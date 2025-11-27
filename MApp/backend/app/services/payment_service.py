"""
Service for payment processing.

Note: This is a simplified implementation with mock payment gateway.
In production, integrate with actual Stripe/Razorpay SDK.
"""
import json
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models.hotel import Payment, PaymentStatus, PaymentMethod, Invoice, InvoiceStatus, Booking
from app.schemas.payment import PaymentResponse


class PaymentService:
    """Service for managing payments."""
    
    @staticmethod
    async def create_payment(
        db: AsyncSession,
        booking_id: int,
        user_id: str,
        amount: Optional[float] = None,
        currency: str = "USD",
        return_url: Optional[str] = None
    ) -> PaymentResponse:
        """
        Create a payment for a booking.
        
        Args:
            db: Database session
            booking_id: ID of the booking
            user_id: Mobile number of the user (from JWT, for authorization)
            amount: Payment amount (defaults to invoice total)
            currency: Currency code
            return_url: URL to redirect after payment
            
        Returns:
            PaymentResponse with payment details and client_secret
        """
        # Convert mobile number to actual user ID
        from app.models.hotel import User
        user_query = select(User.id).where(User.mobile_number == user_id)
        user_result = await db.execute(user_query)
        actual_user_id = user_result.scalar_one_or_none()
        
        if not actual_user_id:
            raise ValueError(f"User with mobile {user_id} not found")
        
        # Get invoice for booking
        invoice_query = (
            select(Invoice)
            .join(Booking)
            .where(
                Invoice.booking_id == booking_id,
                Booking.user_id == actual_user_id
            )
        )
        result = await db.execute(invoice_query)
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            raise ValueError("Invoice not found for this booking")
        
        # Use invoice total if amount not specified
        if amount is None:
            amount = invoice.total_amount
        
        # Validate amount doesn't exceed invoice total
        if amount > invoice.total_amount:
            raise ValueError(f"Payment amount ${amount} exceeds invoice total ${invoice.total_amount}")
        
        # Create payment record
        # In production, this would create a Stripe PaymentIntent or Razorpay Order
        gateway_payment_id = f"pi_mock_{booking_id}_{datetime.utcnow().timestamp()}"
        
        payment = Payment(
            booking_id=booking_id,
            invoice_id=invoice.id,
            amount=amount,
            currency=currency,
            gateway="stripe",  # or razorpay
            gateway_payment_id=gateway_payment_id,
            status=PaymentStatus.PENDING,
            payment_metadata=json.dumps({
                "return_url": return_url,
                "created_by": user_id
            })
        )
        
        db.add(payment)
        await db.commit()
        await db.refresh(payment)
        
        # In production, this would be the actual Stripe client_secret
        # For mock, we'll use a test secret
        client_secret = f"{gateway_payment_id}_secret_mock"
        
        return PaymentResponse(
            id=payment.id,
            booking_id=payment.booking_id,
            invoice_id=payment.invoice_id,
            amount=payment.amount,
            currency=payment.currency,
            payment_method=payment.payment_method.value if payment.payment_method else None,
            gateway=payment.gateway,
            gateway_payment_id=payment.gateway_payment_id,
            status=payment.status.value,
            client_secret=client_secret,
            payment_url=f"/payments/{payment.id}/confirm",  # Mock payment URL
            created_at=payment.created_at
        )
    
    @staticmethod
    async def confirm_payment(
        db: AsyncSession,
        payment_id: int,
        gateway_payment_id: str,
        payment_method: Optional[str] = None
    ) -> Payment:
        """
        Confirm a payment (simulates successful payment).
        
        In production, this would be called by the webhook handler
        after verifying the payment with Stripe/Razorpay.
        
        Args:
            db: Database session
            payment_id: ID of the payment
            gateway_payment_id: Payment ID from gateway
            payment_method: Payment method used
            
        Returns:
            Updated Payment
        """
        # Get payment with related data
        payment_query = (
            select(Payment)
            .options(
                joinedload(Payment.invoice),
                joinedload(Payment.booking)
            )
            .where(
                Payment.id == payment_id,
                Payment.gateway_payment_id == gateway_payment_id
            )
        )
        result = await db.execute(payment_query)
        payment = result.unique().scalar_one_or_none()
        
        if not payment:
            raise ValueError("Payment not found")
        
        if payment.status == PaymentStatus.COMPLETED:
            # Already completed
            return payment
        
        # Update payment status
        payment.status = PaymentStatus.COMPLETED
        payment.paid_at = datetime.utcnow()
        
        if payment_method:
            try:
                payment.payment_method = PaymentMethod(payment_method.lower())
            except ValueError:
                pass  # Invalid payment method, leave as None
        
        # Update invoice status
        invoice = payment.invoice
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = datetime.utcnow()
        
        # Check if booking is fully paid
        booking = payment.booking
        total_paid = await PaymentService.get_total_paid(db, booking.id)
        
        if total_paid >= invoice.total_amount:
            # Fully paid
            invoice.status = InvoiceStatus.PAID
        
        await db.commit()
        await db.refresh(payment)
        
        return payment
    
    @staticmethod
    async def fail_payment(
        db: AsyncSession,
        payment_id: int,
        failure_reason: str
    ) -> Payment:
        """
        Mark a payment as failed.
        
        Args:
            db: Database session
            payment_id: ID of the payment
            failure_reason: Reason for failure
            
        Returns:
            Updated Payment
        """
        payment = await db.get(Payment, payment_id)
        if not payment:
            raise ValueError("Payment not found")
        
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = failure_reason
        
        await db.commit()
        await db.refresh(payment)
        
        return payment
    
    @staticmethod
    async def get_total_paid(
        db: AsyncSession,
        booking_id: int
    ) -> float:
        """
        Get total amount paid for a booking.
        
        Args:
            db: Database session
            booking_id: ID of the booking
            
        Returns:
            Total amount paid
        """
        payments_query = select(Payment).where(
            Payment.booking_id == booking_id,
            Payment.status == PaymentStatus.COMPLETED
        )
        result = await db.execute(payments_query)
        payments = result.scalars().all()
        
        return sum(p.amount for p in payments)
    
    @staticmethod
    async def get_payment_by_id(
        db: AsyncSession,
        payment_id: int,
        user_id: str
    ) -> Optional[Payment]:
        """
        Get payment by ID with authorization check.
        
        Args:
            db: Database session
            payment_id: ID of the payment
            user_id: Mobile number of the user (from JWT, for authorization)
            
        Returns:
            Payment or None
        """
        # Convert mobile number to actual user ID
        from app.models.hotel import User
        user_query = select(User.id).where(User.mobile_number == user_id)
        user_result = await db.execute(user_query)
        actual_user_id = user_result.scalar_one_or_none()
        
        if not actual_user_id:
            return None
        
        payment_query = (
            select(Payment)
            .join(Booking)
            .where(
                Payment.id == payment_id,
                Booking.user_id == actual_user_id
            )
        )
        result = await db.execute(payment_query)
        return result.scalar_one_or_none()
