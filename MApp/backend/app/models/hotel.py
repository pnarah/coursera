from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.db.base import Base


class UserRole(str, enum.Enum):
    GUEST = "guest"
    ADMIN = "admin"
    STAFF = "staff"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    mobile_number = Column(String(15), unique=True, nullable=False, index=True)
    country_code = Column(String(5), nullable=False, default="+1")
    email = Column(String(255), unique=True, nullable=True, index=True)
    full_name = Column(String(255), nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.GUEST, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    bookings = relationship("Booking", back_populates="user")


class Location(Base):
    __tablename__ = "locations"
    
    id = Column(Integer, primary_key=True, index=True)
    country = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=True)
    city = Column(String(100), nullable=False, index=True)
    postal_code = Column(String(20), nullable=True)
    timezone = Column(String(50), nullable=False, default="UTC")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    hotels = relationship("Hotel", back_populates="location")


class Hotel(Base):
    __tablename__ = "hotels"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    address = Column(Text, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    star_rating = Column(Integer, nullable=True)  # 1-5
    contact_number = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    check_in_time = Column(String(10), nullable=False, default="14:00")  # HH:MM
    check_out_time = Column(String(10), nullable=False, default="11:00")  # HH:MM
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    location = relationship("Location", back_populates="hotels")
    rooms = relationship("Room", back_populates="hotel")
    services = relationship("Service", back_populates="hotel")


class RoomType(str, enum.Enum):
    SINGLE = "SINGLE"
    DOUBLE = "DOUBLE"
    DELUXE = "DELUXE"
    SUITE = "SUITE"
    FAMILY = "FAMILY"


class Room(Base):
    __tablename__ = "rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=False)
    room_number = Column(String(20), nullable=False)
    room_type = Column(SQLEnum(RoomType), nullable=False)
    floor_number = Column(Integer, nullable=True)
    capacity = Column(Integer, nullable=False, default=2)
    base_price = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    amenities = Column(Text, nullable=True)  # JSON string: ["WiFi", "TV", "AC"]
    is_available = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    hotel = relationship("Hotel", back_populates="rooms")
    bookings = relationship("Booking", back_populates="room")


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"


class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    check_in_date = Column(DateTime(timezone=True), nullable=False, index=True)
    check_out_date = Column(DateTime(timezone=True), nullable=False, index=True)
    guest_name = Column(String(255), nullable=False)
    guest_email = Column(String(255), nullable=True)
    guest_phone = Column(String(20), nullable=True)
    number_of_guests = Column(Integer, nullable=False, default=1)
    total_amount = Column(Float, nullable=False)
    status = Column(SQLEnum(BookingStatus), default=BookingStatus.PENDING, nullable=False, index=True)
    special_requests = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="bookings")
    room = relationship("Room", back_populates="bookings")
    services = relationship("ServiceOrder", back_populates="booking")
    guests = relationship("Guest", back_populates="booking", cascade="all, delete-orphan")


class Guest(Base):
    __tablename__ = "guests"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    guest_name = Column(String(255), nullable=False)
    guest_email = Column(String(255), nullable=True)
    guest_phone = Column(String(20), nullable=True)
    age = Column(Integer, nullable=True)
    id_type = Column(String(50), nullable=True)  # passport, driver_license, national_id, etc.
    id_number = Column(String(100), nullable=True)
    is_primary = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    booking = relationship("Booking", back_populates="guests")


class ServiceType(str, enum.Enum):
    CAB_PICKUP = "cab_pickup"
    FOOD = "food"
    LAUNDRY = "laundry"
    LEISURE = "leisure"
    ROOM_SERVICE = "room_service"


class Service(Base):
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"), nullable=False)
    name = Column(String(255), nullable=False)
    service_type = Column(SQLEnum(ServiceType), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    hotel = relationship("Hotel", back_populates="services")


class ServiceOrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ServiceOrder(Base):
    __tablename__ = "service_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(SQLEnum(ServiceOrderStatus), default=ServiceOrderStatus.PENDING, nullable=False)
    notes = Column(Text, nullable=True)
    ordered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    booking = relationship("Booking", back_populates="services")
    service = relationship("Service")


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    CANCELLED = "cancelled"


class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, unique=True, index=True)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Amount breakdown
    room_subtotal = Column(Float, nullable=False, default=0.0)  # Room charges
    services_subtotal = Column(Float, nullable=False, default=0.0)  # Service charges
    subtotal = Column(Float, nullable=False, default=0.0)  # room + services
    tax_rate = Column(Float, nullable=False, default=0.18)  # 18% GST/VAT
    tax_amount = Column(Float, nullable=False, default=0.0)
    discount_amount = Column(Float, nullable=False, default=0.0)
    total_amount = Column(Float, nullable=False, default=0.0)  # subtotal + tax - discount
    
    # Metadata
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False, index=True)
    issued_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    booking = relationship("Booking", backref="invoice", uselist=False)


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    UPI = "upi"
    NET_BANKING = "net_banking"
    WALLET = "wallet"


class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    
    # Payment details
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")  # USD, INR, etc.
    payment_method = Column(SQLEnum(PaymentMethod), nullable=True)
    
    # Gateway details
    gateway = Column(String(50), nullable=False, default="stripe")  # stripe, razorpay, etc.
    gateway_payment_id = Column(String(255), nullable=True, index=True)  # Stripe payment_intent_id
    gateway_customer_id = Column(String(255), nullable=True)
    
    # Status tracking
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    failure_reason = Column(Text, nullable=True)
    
    # Additional data
    payment_metadata = Column(Text, nullable=True)  # JSON string for additional data
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    booking = relationship("Booking", backref="payments")
    invoice = relationship("Invoice", backref="payments")


