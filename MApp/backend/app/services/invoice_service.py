"""
Service for invoice generation and management.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models.hotel import Invoice, InvoiceStatus, Booking, ServiceOrder, ServiceOrderStatus
from app.schemas.invoice import InvoiceDetail, InvoiceLineItem


class InvoiceService:
    """Service for managing invoices."""
    
    @staticmethod
    def generate_invoice_number(booking_id: int) -> str:
        """
        Generate a unique invoice number.
        
        Format: INV-YYYYMMDD-BOOKINGID
        Example: INV-20251127-00123
        """
        date_str = datetime.utcnow().strftime("%Y%m%d")
        return f"INV-{date_str}-{booking_id:05d}"
    
    @staticmethod
    async def create_invoice(
        db: AsyncSession,
        booking_id: int,
        room_subtotal: float,
        tax_rate: float = 0.18
    ) -> Invoice:
        """
        Create a new invoice for a booking.
        
        Args:
            db: Database session
            booking_id: ID of the booking
            room_subtotal: Total room charges
            tax_rate: Tax rate (default 18% GST)
            
        Returns:
            Created Invoice
        """
        invoice_number = InvoiceService.generate_invoice_number(booking_id)
        
        # Calculate totals
        subtotal = room_subtotal
        tax_amount = subtotal * tax_rate
        total_amount = subtotal + tax_amount
        
        invoice = Invoice(
            booking_id=booking_id,
            invoice_number=invoice_number,
            room_subtotal=room_subtotal,
            services_subtotal=0.0,
            subtotal=subtotal,
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            discount_amount=0.0,
            total_amount=total_amount,
            status=InvoiceStatus.DRAFT
        )
        
        db.add(invoice)
        await db.commit()
        await db.refresh(invoice)
        
        return invoice
    
    @staticmethod
    async def recalculate_invoice(
        db: AsyncSession,
        invoice_id: int
    ) -> Invoice:
        """
        Recalculate invoice totals based on current booking and service orders.
        
        Args:
            db: Database session
            invoice_id: ID of the invoice
            
        Returns:
            Updated Invoice
        """
        # Get invoice with booking and service orders
        invoice_query = (
            select(Invoice)
            .options(
                joinedload(Invoice.booking)
                .joinedload(Booking.services)
                .joinedload(ServiceOrder.service)
            )
            .where(Invoice.id == invoice_id)
        )
        result = await db.execute(invoice_query)
        invoice = result.unique().scalar_one_or_none()
        
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        booking = invoice.booking
        
        # Calculate room charges (from booking.total_amount initially set during booking)
        # Room charges = booking room price * nights
        # Note: booking.total_amount already includes initial room cost
        # We need to recalculate based on room base price and stay duration
        check_in = booking.check_in_date
        check_out = booking.check_out_date
        nights = (check_out - check_in).days
        
        # Get room base price
        room_query = select(Booking).options(joinedload(Booking.room)).where(Booking.id == booking.id)
        room_result = await db.execute(room_query)
        booking_with_room = room_result.unique().scalar_one()
        room_price = booking_with_room.room.base_price
        
        room_subtotal = room_price * nights
        
        # Calculate service charges (only COMPLETED services)
        services_subtotal = sum(
            order.total_price
            for order in booking.services
            if order.status == ServiceOrderStatus.COMPLETED
        )
        
        # Calculate totals
        subtotal = room_subtotal + services_subtotal
        tax_amount = subtotal * invoice.tax_rate
        total_amount = subtotal + tax_amount - invoice.discount_amount
        
        # Update invoice
        invoice.room_subtotal = room_subtotal
        invoice.services_subtotal = services_subtotal
        invoice.subtotal = subtotal
        invoice.tax_amount = tax_amount
        invoice.total_amount = total_amount
        
        await db.commit()
        await db.refresh(invoice)
        
        return invoice
    
    @staticmethod
    async def get_invoice_by_booking_id(
        db: AsyncSession,
        booking_id: int,
        user_id: int
    ) -> Optional[InvoiceDetail]:
        """
        Get invoice for a booking with line items.
        
        Args:
            db: Database session
            booking_id: ID of the booking
            user_id: ID of the user (for authorization)
            
        Returns:
            InvoiceDetail or None
        """
        # Get invoice with all related data
        invoice_query = (
            select(Invoice)
            .join(Booking)
            .options(
                joinedload(Invoice.booking)
                .joinedload(Booking.services)
                .joinedload(ServiceOrder.service)
            )
            .options(
                joinedload(Invoice.booking).joinedload(Booking.room)
            )
            .where(
                Invoice.booking_id == booking_id,
                Booking.user_id == user_id
            )
        )
        result = await db.execute(invoice_query)
        invoice = result.unique().scalar_one_or_none()
        
        if not invoice:
            return None
        
        booking = invoice.booking
        
        # Build line items
        line_items = []
        
        # Add room charges
        check_in = booking.check_in_date
        check_out = booking.check_out_date
        nights = (check_out - check_in).days
        room_price = booking.room.base_price
        
        line_items.append(InvoiceLineItem(
            description=f"{booking.room.room_type.value.title()} Room - {nights} night(s)",
            item_type="room",
            quantity=nights,
            unit_price=room_price,
            total_price=invoice.room_subtotal,
            status=None
        ))
        
        # Add service charges
        for service_order in booking.services:
            line_items.append(InvoiceLineItem(
                description=f"{service_order.service.name}",
                item_type="service",
                quantity=service_order.quantity,
                unit_price=service_order.unit_price,
                total_price=service_order.total_price,
                status=service_order.status.value
            ))
        
        return InvoiceDetail(
            id=invoice.id,
            booking_id=invoice.booking_id,
            invoice_number=invoice.invoice_number,
            line_items=line_items,
            room_subtotal=invoice.room_subtotal,
            services_subtotal=invoice.services_subtotal,
            subtotal=invoice.subtotal,
            tax_rate=invoice.tax_rate,
            tax_amount=invoice.tax_amount,
            discount_amount=invoice.discount_amount,
            total_amount=invoice.total_amount,
            status=invoice.status.value,
            issued_at=invoice.issued_at,
            paid_at=invoice.paid_at,
            created_at=invoice.created_at,
            updated_at=invoice.updated_at
        )
    
    @staticmethod
    async def issue_invoice(
        db: AsyncSession,
        invoice_id: int
    ) -> Invoice:
        """
        Mark invoice as issued.
        
        Args:
            db: Database session
            invoice_id: ID of the invoice
            
        Returns:
            Updated Invoice
        """
        invoice = await db.get(Invoice, invoice_id)
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        invoice.status = InvoiceStatus.ISSUED
        invoice.issued_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(invoice)
        
        return invoice
