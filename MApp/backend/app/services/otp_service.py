import random
import logging
from redis.asyncio import Redis
from typing import Optional

logger = logging.getLogger(__name__)


class OTPService:
    """Service for OTP generation, storage, and verification."""
    
    OTP_PREFIX = "otp"
    RATE_LIMIT_PREFIX = "otp_rate"
    
    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """Generate random OTP of specified length."""
        return str(random.randint(10**(length-1), 10**length - 1))
    
    @staticmethod
    async def store_otp(redis: Redis, mobile: str, otp: str, ttl: int = 300) -> None:
        """
        Store OTP in Redis with TTL.
        
        Args:
            redis: Redis client
            mobile: Mobile number
            otp: OTP code
            ttl: Time to live in seconds (default 5 minutes)
        """
        key = f"{OTPService.OTP_PREFIX}:{mobile}"
        await redis.setex(key, ttl, otp)
        logger.info(f"OTP stored for mobile: {mobile[:4]}***{mobile[-3:]} (TTL: {ttl}s)")
    
    @staticmethod
    async def verify_otp(redis: Redis, mobile: str, otp: str) -> bool:
        """
        Verify OTP for mobile number.
        
        Args:
            redis: Redis client
            mobile: Mobile number
            otp: OTP code to verify
            
        Returns:
            True if OTP is valid, False otherwise
        """
        key = f"{OTPService.OTP_PREFIX}:{mobile}"
        stored_otp = await redis.get(key)
        
        if stored_otp and stored_otp == otp:
            # Delete OTP after successful verification
            await redis.delete(key)
            logger.info(f"OTP verified successfully for mobile: {mobile[:4]}***{mobile[-3:]}")
            return True
        
        logger.warning(f"OTP verification failed for mobile: {mobile[:4]}***{mobile[-3:]}")
        return False
    
    @staticmethod
    async def check_rate_limit(redis: Redis, mobile: str, max_attempts: int = 3, window: int = 1800) -> bool:
        """
        Check if mobile number has exceeded rate limit.
        
        Args:
            redis: Redis client
            mobile: Mobile number
            max_attempts: Maximum OTP requests allowed
            window: Time window in seconds (default 30 minutes)
            
        Returns:
            True if within rate limit, False if exceeded
        """
        key = f"{OTPService.RATE_LIMIT_PREFIX}:{mobile}"
        current_count = await redis.get(key)
        
        if current_count is None:
            # First request, set counter to 1
            await redis.setex(key, window, "1")
            return True
        
        count = int(current_count)
        if count >= max_attempts:
            logger.warning(f"Rate limit exceeded for mobile: {mobile[:4]}***{mobile[-3:]}")
            return False
        
        # Increment counter
        await redis.incr(key)
        return True
    
    @staticmethod
    async def get_remaining_attempts(redis: Redis, mobile: str, max_attempts: int = 3) -> int:
        """Get remaining OTP request attempts."""
        key = f"{OTPService.RATE_LIMIT_PREFIX}:{mobile}"
        current_count = await redis.get(key)
        
        if current_count is None:
            return max_attempts
        
        count = int(current_count)
        return max(0, max_attempts - count)
    
    @staticmethod
    async def send_otp_sms(mobile: str, otp: str) -> bool:
        """
        Send OTP via SMS (mock implementation).
        In production, integrate with Twilio, AWS SNS, or similar service.
        
        Args:
            mobile: Mobile number
            otp: OTP code
            
        Returns:
            True if SMS sent successfully
        """
        # TODO: Integrate with SMS provider
        logger.info(f"📱 [MOCK SMS] Sending OTP {otp} to {mobile}")
        print(f"\n{'='*50}")
        print(f"📱 SMS to {mobile}")
        print(f"Your MApp verification code is: {otp}")
        print(f"Valid for 5 minutes. Do not share this code.")
        print(f"{'='*50}\n")
        return True
