# Task 03: Session Management System

**Priority:** High  
**Estimated Duration:** 3 days  
**Dependencies:** TASK_01_CORE_AUTHENTICATION, TASK_02_USER_ROLES_AND_RBAC  
**Status:** Not Started

---

## Overview

Implement comprehensive session management using Redis for tracking user sessions across multiple devices, with role-based timeouts, automatic cleanup, and multi-device support.

---

## Objectives

1. Create Redis-based session storage
2. Implement role-specific session timeouts
3. Add multi-device session tracking
4. Create session cleanup jobs
5. Add session invalidation on security events
6. Implement session listing and management
7. Add frontend session restoration

---

## Backend Tasks

### 1. Database Schema

Create migration `003_create_sessions_table.py`:

```sql
-- Session tracking table (for persistent storage)
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    device_info TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_activity TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT true,
    invalidated_at TIMESTAMP,
    invalidation_reason VARCHAR(100)
);

CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_sessions_expires ON user_sessions(expires_at);
CREATE INDEX idx_sessions_active ON user_sessions(is_active);
```

### 2. Session Models

Create `app/models/session.py`:

```python
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base
import uuid

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_info = Column(Text)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    invalidated_at = Column(DateTime(timezone=True))
    invalidation_reason = Column(String(100))
```

### 3. Session Configuration

Update `app/core/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Session Configuration
    SESSION_TIMEOUT_GUEST: int = 86400  # 24 hours
    SESSION_TIMEOUT_EMPLOYEE: int = 28800  # 8 hours
    SESSION_TIMEOUT_VENDOR: int = 43200  # 12 hours
    SESSION_TIMEOUT_ADMIN: int = 14400  # 4 hours
    
    MAX_SESSIONS_GUEST: int = 5
    MAX_SESSIONS_EMPLOYEE: int = 2
    MAX_SESSIONS_VENDOR: int = 3
    MAX_SESSIONS_ADMIN: int = 2
    
    SESSION_REFRESH_THRESHOLD: int = 300  # 5 minutes
```

### 4. Session Service

Create `app/services/session_service.py`:

```python
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from fastapi import HTTPException, Request
from app.models.session import UserSession
from app.models.user import User, UserRole
from app.core.redis import redis_client
from app.core.config import settings

class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def get_session_timeout(self, role: UserRole) -> int:
        """Get session timeout based on user role"""
        timeouts = {
            UserRole.GUEST: settings.SESSION_TIMEOUT_GUEST,
            UserRole.HOTEL_EMPLOYEE: settings.SESSION_TIMEOUT_EMPLOYEE,
            UserRole.VENDOR_ADMIN: settings.SESSION_TIMEOUT_VENDOR,
            UserRole.SYSTEM_ADMIN: settings.SESSION_TIMEOUT_ADMIN,
        }
        return timeouts.get(role, settings.SESSION_TIMEOUT_GUEST)
    
    def get_max_sessions(self, role: UserRole) -> int:
        """Get maximum allowed sessions based on user role"""
        max_sessions = {
            UserRole.GUEST: settings.MAX_SESSIONS_GUEST,
            UserRole.HOTEL_EMPLOYEE: settings.MAX_SESSIONS_EMPLOYEE,
            UserRole.VENDOR_ADMIN: settings.MAX_SESSIONS_VENDOR,
            UserRole.SYSTEM_ADMIN: settings.MAX_SESSIONS_ADMIN,
        }
        return max_sessions.get(role, settings.MAX_SESSIONS_GUEST)
    
    async def create_session(
        self,
        user: User,
        access_token: str,
        refresh_token: str,
        request: Request
    ) -> UserSession:
        """Create new session for user"""
        # Check max sessions limit
        await self._enforce_max_sessions(user)
        
        # Get device info
        device_info = self._extract_device_info(request)
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")
        
        # Calculate expiry
        timeout = self.get_session_timeout(user.role)
        expires_at = datetime.utcnow() + timedelta(seconds=timeout)
        
        # Create session in database
        session = UserSession(
            user_id=user.id,
            device_info=device_info,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
            is_active=True
        )
        
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        
        # Store session in Redis
        session_data = {
            "user_id": user.id,
            "session_id": str(session.id),
            "role": user.role.value,
            "hotel_id": user.hotel_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "last_activity": datetime.utcnow().isoformat(),
        }
        
        redis_key = f"session:{user.id}:{session.id}"
        await redis_client.setex(
            redis_key,
            timeout,
            json.dumps(session_data)
        )
        
        return session
    
    async def get_session(self, user_id: int, session_id: UUID) -> Optional[Dict]:
        """Get session from Redis"""
        redis_key = f"session:{user_id}:{session_id}"
        session_data = await redis_client.get(redis_key)
        
        if session_data:
            return json.loads(session_data)
        return None
    
    async def update_activity(self, user_id: int, session_id: UUID):
        """Update last activity timestamp"""
        redis_key = f"session:{user_id}:{session_id}"
        session_data = await redis_client.get(redis_key)
        
        if session_data:
            data = json.loads(session_data)
            data["last_activity"] = datetime.utcnow().isoformat()
            
            # Get remaining TTL
            ttl = await redis_client.ttl(redis_key)
            if ttl > 0:
                await redis_client.setex(redis_key, ttl, json.dumps(data))
            
            # Update database
            stmt = select(UserSession).where(UserSession.id == session_id)
            result = await self.db.execute(stmt)
            session = result.scalar_one_or_none()
            if session:
                session.last_activity = datetime.utcnow()
                await self.db.commit()
    
    async def invalidate_session(
        self,
        session_id: UUID,
        reason: str = "user_logout"
    ):
        """Invalidate a specific session"""
        # Get session from database
        stmt = select(UserSession).where(UserSession.id == session_id)
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if session:
            # Update database
            session.is_active = False
            session.invalidated_at = datetime.utcnow()
            session.invalidation_reason = reason
            await self.db.commit()
            
            # Remove from Redis
            redis_key = f"session:{session.user_id}:{session_id}"
            await redis_client.delete(redis_key)
    
    async def invalidate_all_user_sessions(
        self,
        user_id: int,
        except_session: Optional[UUID] = None,
        reason: str = "security_event"
    ):
        """Invalidate all sessions for a user"""
        # Get all active sessions
        stmt = select(UserSession).where(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
        )
        
        if except_session:
            stmt = stmt.where(UserSession.id != except_session)
        
        result = await self.db.execute(stmt)
        sessions = result.scalars().all()
        
        for session in sessions:
            await self.invalidate_session(session.id, reason)
    
    async def get_user_sessions(self, user_id: int) -> List[UserSession]:
        """Get all active sessions for a user"""
        stmt = select(UserSession).where(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow()
            )
        ).order_by(UserSession.last_activity.desc())
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def refresh_session(
        self,
        user: User,
        session_id: UUID,
        new_access_token: str
    ):
        """Refresh session with new access token"""
        redis_key = f"session:{user.id}:{session_id}"
        session_data = await redis_client.get(redis_key)
        
        if session_data:
            data = json.loads(session_data)
            data["access_token"] = new_access_token
            data["last_activity"] = datetime.utcnow().isoformat()
            
            # Extend expiry
            timeout = self.get_session_timeout(user.role)
            await redis_client.setex(redis_key, timeout, json.dumps(data))
            
            # Update database
            stmt = select(UserSession).where(UserSession.id == session_id)
            result = await self.db.execute(stmt)
            session = result.scalar_one_or_none()
            if session:
                session.expires_at = datetime.utcnow() + timedelta(seconds=timeout)
                session.last_activity = datetime.utcnow()
                await self.db.commit()
    
    async def cleanup_expired_sessions(self):
        """Remove expired sessions (background job)"""
        # Delete from database
        stmt = delete(UserSession).where(
            and_(
                UserSession.is_active == True,
                UserSession.expires_at < datetime.utcnow()
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def _enforce_max_sessions(self, user: User):
        """Ensure user doesn't exceed maximum session limit"""
        sessions = await self.get_user_sessions(user.id)
        max_allowed = self.get_max_sessions(user.role)
        
        if len(sessions) >= max_allowed:
            # Remove oldest session
            oldest = sessions[-1]
            await self.invalidate_session(
                oldest.id,
                reason="max_sessions_exceeded"
            )
    
    def _extract_device_info(self, request: Request) -> str:
        """Extract device information from request"""
        user_agent = request.headers.get("user-agent", "")
        
        # Simple device detection
        if "Mobile" in user_agent:
            if "iPhone" in user_agent:
                return "iPhone"
            elif "Android" in user_agent:
                return "Android"
            return "Mobile"
        elif "iPad" in user_agent:
            return "iPad"
        elif "Macintosh" in user_agent:
            return "Mac"
        elif "Windows" in user_agent:
            return "Windows"
        elif "Linux" in user_agent:
            return "Linux"
        
        return "Unknown"
```

### 5. Update Authentication Middleware

Update `app/core/dependencies.py`:

```python
from app.services.session_service import SessionService

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user and validate session"""
    try:
        token = credentials.credentials
        payload = decode_token(token)
        user_id = payload.get("user_id")
        session_id = payload.get("session_id")  # Add session_id to JWT
        
        if not user_id or not session_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Check session in Redis
        session_service = SessionService(db)
        session_data = await session_service.get_session(user_id, session_id)
        
        if not session_data:
            raise HTTPException(
                status_code=401,
                detail="Session expired or invalid"
            )
        
        # Get user from database
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User inactive")
        
        # Update activity
        await session_service.update_activity(user_id, session_id)
        
        # Attach session_id to user for later use
        user.current_session_id = session_id
        
        return user
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### 6. Session API Endpoints

Create `app/api/v1/sessions.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.db.session import get_db
from app.models.user import User
from app.models.session import UserSession
from app.services.session_service import SessionService
from app.core.dependencies import get_current_user
from app.schemas.session import SessionResponse

router = APIRouter(prefix="/sessions", tags=["Sessions"])

@router.get("/", response_model=List[SessionResponse])
async def list_my_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all active sessions for current user"""
    session_service = SessionService(db)
    sessions = await session_service.get_user_sessions(current_user.id)
    
    return [
        {
            "id": str(session.id),
            "device_info": session.device_info,
            "ip_address": session.ip_address,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "is_current": str(session.id) == str(current_user.current_session_id)
        }
        for session in sessions
    ]

@router.delete("/{session_id}")
async def logout_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout from specific session"""
    session_service = SessionService(db)
    await session_service.invalidate_session(session_id, "user_logout")
    
    return {"success": True, "message": "Session logged out"}

@router.delete("/")
async def logout_all_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout from all sessions except current"""
    session_service = SessionService(db)
    await session_service.invalidate_all_user_sessions(
        current_user.id,
        except_session=current_user.current_session_id,
        reason="user_logout_all"
    )
    
    return {"success": True, "message": "All other sessions logged out"}
```

### 7. Background Job

Create `app/jobs/session_cleanup.py`:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.db.session import get_async_db
from app.services.session_service import SessionService

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour='*')  # Every hour
async def cleanup_expired_sessions():
    """Clean up expired sessions"""
    async for db in get_async_db():
        session_service = SessionService(db)
        await session_service.cleanup_expired_sessions()
        print(f"Session cleanup completed at {datetime.utcnow()}")

def start_session_cleanup_job():
    """Start the session cleanup scheduler"""
    scheduler.start()
```

---

## Frontend Tasks

### 1. Session State Management

Update `mobile/lib/core/providers/auth_provider.dart`:

```dart
class AuthNotifier extends StateNotifier<AuthState> {
  // ... existing code ...
  
  Timer? _activityTimer;
  Timer? _refreshTimer;
  
  void startSessionMonitoring() {
    // Monitor for token expiry
    _refreshTimer = Timer.periodic(
      const Duration(minutes: 5),
      (_) => _checkAndRefreshToken(),
    );
    
    // Track user activity
    _activityTimer = Timer.periodic(
      const Duration(minutes: 1),
      (_) => _updateActivity(),
    );
  }
  
  Future<void> _checkAndRefreshToken() async {
    final token = await _storage.getAccessToken();
    if (token == null) return;
    
    // Decode token and check expiry
    final parts = token.split('.');
    if (parts.length != 3) return;
    
    final payload = json.decode(
      utf8.decode(base64.decode(base64.normalize(parts[1])))
    );
    
    final exp = DateTime.fromMillisecondsSinceEpoch(payload['exp'] * 1000);
    final now = DateTime.now();
    
    // Refresh if expiring in < 5 minutes
    if (exp.difference(now).inMinutes < 5) {
      await _refreshToken();
    }
  }
  
  Future<void> _refreshToken() async {
    try {
      final refreshToken = await _storage.getRefreshToken();
      if (refreshToken == null) {
        await logout();
        return;
      }
      
      final result = await _apiService.refreshToken(refreshToken);
      await _storage.saveTokens(
        result['access_token'],
        refreshToken,
      );
    } catch (e) {
      await logout();
    }
  }
  
  Future<void> _updateActivity() async {
    // Activity is updated automatically via API calls
    // This is just a heartbeat check
  }
  
  @override
  void dispose() {
    _activityTimer?.cancel();
    _refreshTimer?.cancel();
    super.dispose();
  }
}
```

### 2. Session Management Screen

Create `mobile/lib/features/profile/active_sessions_screen.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class ActiveSessionsScreen extends ConsumerStatefulWidget {
  const ActiveSessionsScreen({Key? key}) : super(key: key);

  @override
  ConsumerState<ActiveSessionsScreen> createState() => _ActiveSessionsScreenState();
}

class _ActiveSessionsScreenState extends ConsumerState<ActiveSessionsScreen> {
  List<Map<String, dynamic>> _sessions = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadSessions();
  }

  Future<void> _loadSessions() async {
    setState(() => _isLoading = true);
    try {
      final sessions = await ApiService().getMySessions();
      setState(() {
        _sessions = sessions;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to load sessions: $e')),
      );
    }
  }

  Future<void> _logoutSession(String sessionId) async {
    try {
      await ApiService().logoutSession(sessionId);
      await _loadSessions();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Session logged out successfully')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to logout session: $e')),
      );
    }
  }

  Future<void> _logoutAllSessions() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Logout All Devices'),
        content: const Text(
          'Are you sure you want to logout from all other devices?'
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Logout All'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await ApiService().logoutAllSessions();
        await _loadSessions();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Logged out from all other devices')),
        );
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Active Sessions'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: _sessions.length > 1 ? _logoutAllSessions : null,
            tooltip: 'Logout all other devices',
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadSessions,
              child: ListView.builder(
                itemCount: _sessions.length,
                itemBuilder: (context, index) {
                  final session = _sessions[index];
                  final isCurrent = session['is_current'] == true;
                  
                  return ListTile(
                    leading: Icon(
                      _getDeviceIcon(session['device_info']),
                      color: isCurrent ? Colors.green : Colors.grey,
                    ),
                    title: Text(
                      session['device_info'] ?? 'Unknown Device',
                      style: TextStyle(
                        fontWeight: isCurrent ? FontWeight.bold : FontWeight.normal,
                      ),
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('IP: ${session['ip_address'] ?? 'Unknown'}'),
                        Text(
                          'Last active: ${_formatDateTime(session['last_activity'])}',
                          style: const TextStyle(fontSize: 12),
                        ),
                      ],
                    ),
                    trailing: isCurrent
                        ? const Chip(
                            label: Text('Current'),
                            backgroundColor: Colors.green,
                            labelStyle: TextStyle(color: Colors.white),
                          )
                        : IconButton(
                            icon: const Icon(Icons.logout),
                            onPressed: () => _logoutSession(session['id']),
                          ),
                  );
                },
              ),
            ),
    );
  }

  IconData _getDeviceIcon(String? device) {
    switch (device?.toLowerCase()) {
      case 'iphone':
      case 'android':
        return Icons.phone_android;
      case 'ipad':
        return Icons.tablet;
      case 'mac':
      case 'windows':
      case 'linux':
        return Icons.computer;
      default:
        return Icons.devices;
    }
  }

  String _formatDateTime(dynamic dateTime) {
    if (dateTime == null) return 'Unknown';
    final dt = DateTime.parse(dateTime.toString());
    final now = DateTime.now();
    final diff = now.difference(dt);
    
    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
  }
}
```

---

## Acceptance Criteria

- ✅ Sessions stored in Redis with role-based timeouts
- ✅ Session data persisted to PostgreSQL
- ✅ Multi-device support with device tracking
- ✅ Max sessions enforced per role
- ✅ Automatic session cleanup job runs hourly
- ✅ Session invalidation on logout/security events
- ✅ Activity tracking updates last_activity
- ✅ Frontend auto-refreshes tokens before expiry
- ✅ Users can view active sessions
- ✅ Users can logout from specific sessions
- ✅ Users can logout from all other sessions

---

## Next Task

**TASK_04_SUBSCRIPTION_MANAGEMENT.md** - Implement subscription plans and lifecycle management
