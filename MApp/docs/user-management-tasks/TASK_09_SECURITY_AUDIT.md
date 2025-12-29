# Task 09: Security Audit & Hardening

**Priority:** Critical  
**Estimated Duration:** 3-4 days  
**Dependencies:** ALL Tasks (TASK_01 through TASK_08)  
**Status:** Not Started

---

## Overview

Comprehensive security audit, penetration testing, and hardening of the entire MApp platform. Ensure compliance with security best practices and industry standards.

---

## Objectives

1. Conduct security vulnerability assessment
2. Implement rate limiting and DDoS protection
3. Add input validation and sanitization
4. Secure API endpoints with proper authentication
5. Implement HTTPS and SSL/TLS
6. Add security headers and CSP
7. Conduct penetration testing
8. Implement audit logging
9. Data encryption at rest and in transit
10. Compliance checks (GDPR, PCI-DSS basics)

---

## Security Checklist

### 1. Authentication & Authorization

#### Backend Hardening

**File:** `app/core/security.py`

```python
from fastapi import HTTPException, status, Request
from functools import wraps
from datetime import datetime, timedelta
from typing import Dict, Optional
import hashlib
import secrets

class SecurityManager:
    """Central security management"""
    
    # Rate limiting storage (use Redis in production)
    _rate_limit_store: Dict[str, list] = {}
    _failed_login_attempts: Dict[str, int] = {}
    _blocked_ips: Dict[str, datetime] = {}
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate cryptographically secure random token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt (already implemented)"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(plain_password, hashed_password)
    
    @classmethod
    def check_rate_limit(
        cls,
        identifier: str,
        max_requests: int = 10,
        window_seconds: int = 60
    ) -> bool:
        """Check if request exceeds rate limit"""
        now = datetime.utcnow()
        
        if identifier not in cls._rate_limit_store:
            cls._rate_limit_store[identifier] = []
        
        # Remove old requests outside window
        cls._rate_limit_store[identifier] = [
            req_time for req_time in cls._rate_limit_store[identifier]
            if now - req_time < timedelta(seconds=window_seconds)
        ]
        
        # Check if limit exceeded
        if len(cls._rate_limit_store[identifier]) >= max_requests:
            return False
        
        # Add current request
        cls._rate_limit_store[identifier].append(now)
        return True
    
    @classmethod
    def record_failed_login(cls, identifier: str) -> int:
        """Record failed login attempt and return count"""
        if identifier not in cls._failed_login_attempts:
            cls._failed_login_attempts[identifier] = 0
        
        cls._failed_login_attempts[identifier] += 1
        
        # Block IP after 5 failed attempts
        if cls._failed_login_attempts[identifier] >= 5:
            cls._blocked_ips[identifier] = datetime.utcnow() + timedelta(hours=1)
        
        return cls._failed_login_attempts[identifier]
    
    @classmethod
    def reset_failed_logins(cls, identifier: str):
        """Reset failed login count on successful login"""
        if identifier in cls._failed_login_attempts:
            del cls._failed_login_attempts[identifier]
        if identifier in cls._blocked_ips:
            del cls._blocked_ips[identifier]
    
    @classmethod
    def is_blocked(cls, identifier: str) -> bool:
        """Check if IP is blocked"""
        if identifier in cls._blocked_ips:
            if datetime.utcnow() < cls._blocked_ips[identifier]:
                return True
            else:
                # Unblock if time passed
                del cls._blocked_ips[identifier]
        return False
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 1000) -> str:
        """Sanitize user input to prevent XSS"""
        import html
        
        # Limit length
        text = text[:max_length]
        
        # Escape HTML
        text = html.escape(text)
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        return text.strip()
    
    @staticmethod
    def validate_mobile_number(mobile: str) -> bool:
        """Validate mobile number format"""
        import re
        # Allow 10-15 digits only
        pattern = r'^\d{10,15}$'
        return bool(re.match(pattern, mobile))
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
```

#### Middleware for Security Headers

**File:** `app/middleware/security_middleware.py`

```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.core.security import SecurityManager
import logging

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        # Check if IP is blocked
        client_ip = request.client.host
        if SecurityManager.is_blocked(client_ip):
            return Response(
                content="Too many failed attempts. Please try again later.",
                status_code=429
            )
        
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Global rate limiting"""
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        
        # Rate limit: 100 requests per minute per IP
        if not SecurityManager.check_rate_limit(client_ip, max_requests=100, window_seconds=60):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return Response(
                content="Rate limit exceeded. Please slow down.",
                status_code=429
            )
        
        response = await call_next(request)
        return response
```

#### Update main.py

**File:** `app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.middleware.security_middleware import SecurityHeadersMiddleware, RateLimitMiddleware
from app.core.config import settings

app = FastAPI(
    title="MApp API",
    version="1.0.0",
    docs_url="/api/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT == "development" else None,
)

# Security middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

# Trusted host middleware (prevent host header injection)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "api.mapp.com", "*.mapp.com"]
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # Configure in settings
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=3600,
)
```

---

### 2. Input Validation & Sanitization

**File:** `app/schemas/validators.py`

```python
from pydantic import BaseModel, Field, field_validator
from app.core.security import SecurityManager

class SecureBaseModel(BaseModel):
    """Base model with automatic input sanitization"""
    
    @field_validator('*', mode='before')
    @classmethod
    def sanitize_strings(cls, v):
        """Sanitize all string inputs"""
        if isinstance(v, str):
            return SecurityManager.sanitize_input(v)
        return v

class MobileNumberValidator(BaseModel):
    mobile_number: str = Field(..., min_length=10, max_length=15)
    
    @field_validator('mobile_number')
    @classmethod
    def validate_mobile(cls, v):
        if not SecurityManager.validate_mobile_number(v):
            raise ValueError("Invalid mobile number format")
        return v

class EmailValidator(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if not SecurityManager.validate_email(v):
            raise ValueError("Invalid email format")
        return v
```

---

### 3. SQL Injection Prevention

✅ **Already Protected**: Using SQLAlchemy ORM with parameterized queries

**Verify all queries use bound parameters:**

```python
# ✅ SAFE - Parameterized query
result = await db.execute(
    select(User).where(User.mobile_number == mobile_number)
)

# ❌ UNSAFE - String concatenation (NEVER DO THIS)
# result = await db.execute(f"SELECT * FROM users WHERE mobile_number = '{mobile_number}'")
```

---

### 4. Data Encryption

#### Encrypt Sensitive Data at Rest

**File:** `app/core/encryption.py`

```python
from cryptography.fernet import Fernet
from app.core.config import settings
import base64

class DataEncryption:
    """Encrypt/decrypt sensitive data"""
    
    _cipher = None
    
    @classmethod
    def _get_cipher(cls):
        if cls._cipher is None:
            # Get encryption key from settings
            key = settings.ENCRYPTION_KEY.encode()
            # Ensure key is 32 bytes for Fernet
            key = base64.urlsafe_b64encode(key.ljust(32)[:32])
            cls._cipher = Fernet(key)
        return cls._cipher
    
    @classmethod
    def encrypt(cls, data: str) -> str:
        """Encrypt string data"""
        cipher = cls._get_cipher()
        encrypted = cipher.encrypt(data.encode())
        return encrypted.decode()
    
    @classmethod
    def decrypt(cls, encrypted_data: str) -> str:
        """Decrypt string data"""
        cipher = cls._get_cipher()
        decrypted = cipher.decrypt(encrypted_data.encode())
        return decrypted.decode()

# Usage example for encrypting PII
class User(Base):
    # ... other fields ...
    
    _email = Column("email", String(255))  # Stored encrypted
    
    @property
    def email(self):
        if self._email:
            return DataEncryption.decrypt(self._email)
        return None
    
    @email.setter
    def email(self, value):
        if value:
            self._email = DataEncryption.encrypt(value)
        else:
            self._email = None
```

---

### 5. Secure Session Management

**Update:** `app/services/session_service.py`

```python
class SessionService:
    # ... existing code ...
    
    async def create_session(
        self,
        user_id: int,
        device_info: str,
        ip_address: str,
        user_agent: str
    ) -> str:
        """Create session with additional security metadata"""
        session_id = secrets.token_urlsafe(32)
        
        session_data = {
            "user_id": user_id,
            "device_info": device_info,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        }
        
        await self.redis.setex(
            f"session:{session_id}",
            settings.SESSION_TIMEOUT,
            json.dumps(session_data)
        )
        
        return session_id
    
    async def validate_session(
        self,
        session_id: str,
        ip_address: str,
        user_agent: str
    ) -> Optional[dict]:
        """Validate session with IP and user agent check"""
        session_data = await self.get_session(session_id)
        
        if not session_data:
            return None
        
        # Check if IP address changed (optional - may cause issues with mobile networks)
        # if session_data.get("ip_address") != ip_address:
        #     logger.warning(f"IP address mismatch for session {session_id}")
        #     return None
        
        # Check if user agent changed
        if session_data.get("user_agent") != user_agent:
            logger.warning(f"User agent mismatch for session {session_id}")
            # Don't invalidate, just log (user might switch browsers)
        
        # Update last activity
        session_data["last_activity"] = datetime.utcnow().isoformat()
        await self.redis.setex(
            f"session:{session_id}",
            settings.SESSION_TIMEOUT,
            json.dumps(session_data)
        )
        
        return session_data
```

---

### 6. Environment Variables Security

**Update:** `.env.example`

```env
# DO NOT commit .env file to git
# This is just a template

# Security
SECRET_KEY=CHANGE_THIS_TO_RANDOM_STRING_MIN_32_CHARS
ENCRYPTION_KEY=CHANGE_THIS_TO_ANOTHER_RANDOM_STRING_32_CHARS
JWT_SECRET_KEY=CHANGE_THIS_JWT_SECRET_MIN_32_CHARS

# Environment
ENVIRONMENT=production  # production, staging, development

# Allowed origins (comma-separated)
ALLOWED_ORIGINS=https://app.mapp.com,https://www.mapp.com

# Database (use connection pooling)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/mapp_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=your_redis_password

# Rate limiting
RATE_LIMIT_ENABLED=true
MAX_REQUESTS_PER_MINUTE=100
OTP_MAX_ATTEMPTS=3
OTP_RATE_LIMIT_MINUTES=30

# SSL/TLS
SSL_ENABLED=true
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem
```

**.gitignore update:**

```
# Environment
.env
.env.*
!.env.example

# Secrets
secrets/
*.pem
*.key
*.crt
```

---

### 7. HTTPS/SSL Configuration

**File:** `deploy/nginx.conf`

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.mapp.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS configuration
server {
    listen 443 ssl http2;
    server_name api.mapp.com;
    
    # SSL certificates (Let's Encrypt recommended)
    ssl_certificate /etc/letsencrypt/live/api.mapp.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.mapp.com/privkey.pem;
    
    # SSL protocols and ciphers
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy to FastAPI
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
}
```

---

### 8. Penetration Testing Checklist

```markdown
## Manual Security Testing

### Authentication Testing
- [ ] Test OTP brute force prevention
- [ ] Test JWT token expiry
- [ ] Test refresh token rotation
- [ ] Test session hijacking prevention
- [ ] Test concurrent session limits
- [ ] Test password reset flow (if implemented)

### Authorization Testing
- [ ] Test horizontal privilege escalation (user accessing another user's data)
- [ ] Test vertical privilege escalation (guest accessing admin endpoints)
- [ ] Test RBAC enforcement on all endpoints
- [ ] Test multi-tenant isolation (vendor accessing another vendor's hotels)

### Input Validation
- [ ] Test SQL injection on all inputs
- [ ] Test XSS on text fields
- [ ] Test CSRF protection
- [ ] Test file upload vulnerabilities (if implemented)
- [ ] Test API parameter tampering

### Rate Limiting
- [ ] Test OTP rate limiting (3 attempts/30 min)
- [ ] Test API rate limiting (100 req/min)
- [ ] Test login rate limiting

### Data Protection
- [ ] Test HTTPS enforcement
- [ ] Test sensitive data exposure in logs
- [ ] Test data encryption at rest
- [ ] Test secure headers presence
- [ ] Test CORS policy

### Business Logic
- [ ] Test booking double-booking prevention
- [ ] Test payment amount manipulation
- [ ] Test invoice tampering
- [ ] Test subscription bypass
```

---

### 9. Logging & Monitoring

**File:** `app/core/logging_config.py`

```python
import logging
import sys
from datetime import datetime

# Sensitive fields to redact from logs
SENSITIVE_FIELDS = ["password", "otp", "token", "secret", "key"]

class SensitiveDataFilter(logging.Filter):
    """Filter to redact sensitive data from logs"""
    
    def filter(self, record):
        msg = record.getMessage()
        
        # Redact sensitive fields
        for field in SENSITIVE_FIELDS:
            if field in msg.lower():
                # Replace with asterisks
                import re
                pattern = rf'{field}["\s:=]+([^",\s]+)'
                msg = re.sub(pattern, f'{field}=***REDACTED***', msg, flags=re.IGNORECASE)
        
        record.msg = msg
        return True

def setup_logging():
    """Configure application logging"""
    
    # Create logger
    logger = logging.getLogger("mapp")
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # File handler (rotate daily)
    from logging.handlers import TimedRotatingFileHandler
    file_handler = TimedRotatingFileHandler(
        filename='logs/app.log',
        when='midnight',
        interval=1,
        backupCount=30
    )
    file_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add sensitive data filter
    console_handler.addFilter(SensitiveDataFilter())
    file_handler.addFilter(SensitiveDataFilter())
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger
```

---

### 10. Security Audit Tools

**Install security scanning tools:**

```bash
# Python dependency checker
pip install safety
safety check

# Code security scanner
pip install bandit
bandit -r app/

# SQL injection scanner
pip install sqlmap

# API security scanner (manual)
# Use OWASP ZAP or Burp Suite
```

**File:** `scripts/security_audit.sh`

```bash
#!/bin/bash

echo "=== MApp Security Audit ==="
echo ""

echo "1. Checking Python dependencies for vulnerabilities..."
safety check
echo ""

echo "2. Scanning code for security issues..."
bandit -r app/ -f json -o security_report.json
echo ""

echo "3. Checking for exposed secrets..."
git secrets --scan
echo ""

echo "4. Testing SSL configuration..."
curl -I https://api.mapp.com | grep -i "strict-transport-security"
echo ""

echo "Security audit complete. Review security_report.json for details."
```

---

## Testing

```python
# tests/test_security.py
import pytest
from app.core.security import SecurityManager

def test_rate_limiting():
    identifier = "test_ip"
    
    # First 10 requests should succeed
    for i in range(10):
        assert SecurityManager.check_rate_limit(identifier, max_requests=10, window_seconds=60)
    
    # 11th request should fail
    assert not SecurityManager.check_rate_limit(identifier, max_requests=10, window_seconds=60)

def test_failed_login_blocking():
    identifier = "attacker_ip"
    
    # Record 5 failed attempts
    for i in range(5):
        SecurityManager.record_failed_login(identifier)
    
    # Should be blocked
    assert SecurityManager.is_blocked(identifier)

def test_input_sanitization():
    malicious_input = "<script>alert('XSS')</script>"
    sanitized = SecurityManager.sanitize_input(malicious_input)
    
    assert "<script>" not in sanitized
    assert "&lt;script&gt;" in sanitized
```

---

## Compliance Checklist

### GDPR Compliance
- [ ] User consent for data collection
- [ ] Right to access data (API endpoint)
- [ ] Right to delete data (API endpoint)
- [ ] Right to data portability
- [ ] Data breach notification process
- [ ] Privacy policy published
- [ ] Cookie consent (if applicable)

### PCI-DSS Basics (for payment handling)
- [ ] Use certified payment gateway (Stripe)
- [ ] Never store full card numbers
- [ ] Use tokenization
- [ ] Encrypt payment data in transit
- [ ] Implement access controls
- [ ] Regular security testing

---

## Acceptance Criteria

- [ ] All security headers present
- [ ] HTTPS enforced
- [ ] Rate limiting working
- [ ] Input sanitization on all endpoints
- [ ] SQL injection protection verified
- [ ] XSS protection verified
- [ ] RBAC working correctly
- [ ] Session security enhanced
- [ ] Audit logging implemented
- [ ] Penetration testing passed
- [ ] Security scan results reviewed
- [ ] No critical vulnerabilities found
- [ ] Compliance requirements met

---

## Next Task

**[TASK_10_TESTING_DOCUMENTATION.md](./TASK_10_TESTING_DOCUMENTATION.md)** - Comprehensive testing and documentation.
