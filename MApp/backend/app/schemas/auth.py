from pydantic import BaseModel, Field, field_validator
from typing import Optional


class OTPRequest(BaseModel):
    mobile_number: str = Field(..., min_length=10, max_length=15)
    country_code: str = Field(default="+1")

    @field_validator('mobile_number')
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        # Remove any spaces, dashes, or parentheses
        cleaned = ''.join(filter(str.isdigit, v))
        if len(cleaned) < 10 or len(cleaned) > 15:
            raise ValueError('Mobile number must be between 10-15 digits')
        return cleaned


class OTPVerify(BaseModel):
    mobile_number: str
    otp: str = Field(..., min_length=6, max_length=6)
    device_info: str = Field(default="unknown")

    @field_validator('otp')
    @classmethod
    def validate_otp(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError('OTP must contain only digits')
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class OTPResponse(BaseModel):
    message: str
    expires_in: int  # seconds
    mobile_number: str
