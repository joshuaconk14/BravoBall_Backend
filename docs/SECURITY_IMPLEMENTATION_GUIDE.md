# BravoBall Security Implementation Guide

**Document Version:** 1.0  
**Date:** August 21, 2025  
**Author:** BravoBall Development Team  
**Target Audience:** Backend Developers, DevOps Engineers  

## Overview

This guide provides technical implementation details for BravoBall's premium subscription security features. It covers the architecture, code structure, and deployment considerations for the receipt validation, audit logging, and rate limiting systems.

## Architecture Components

### 1. Rate Limiter Service

**Location:** `services/rate_limiter.py`

**Purpose:** In-memory rate limiting per user per endpoint

**Implementation:**
```python
class RateLimiter:
    def __init__(self):
        self.requests = {}  # {user_id: {endpoint: [(timestamp, count)]}}
    
    def allow(self, user_id: int, endpoint: str, limit: int, window_seconds: int) -> bool:
        # Implementation details...
```

**Usage:**
```python
# In router endpoints
if not rate_limiter.allow(current_user.id, "/api/premium/verify-receipt", limit=5, window_seconds=60):
    raise HTTPException(status_code=429, detail="Too many requests")
```

### 2. Audit Service

**Location:** `services/audit_service.py`

**Purpose:** Centralized audit logging for security events

**Implementation:**
```python
class AuditService:
    @staticmethod
    def log(db: Session, *, user_id: Optional[int], action: str, 
            endpoint: str, method: str, status: str, **kwargs) -> None:
        # Implementation details...
```

**Usage:**
```python
# In router endpoints
AuditService.log(
    db,
    user_id=current_user.id,
    action="premium_status",
    endpoint=str(request.url.path),
    method="GET",
    status="success",
    ip_address=request.client.host,
    user_agent=request.headers.get("User-Agent"),
    device_fingerprint=device_fingerprint
)
```

### 3. Receipt Verifier Service

**Location:** `services/receipt_verifier.py`

**Purpose:** Platform-specific receipt validation

**Implementation:**
```python
class ReceiptVerifier:
    def __init__(self):
        self.test_mode = os.getenv("PREMIUM_TEST_MODE", "false").lower() == "true"
    
    async def verify(self, platform: str, receipt_data: str, 
                    product_id: str, transaction_id: str) -> Tuple[bool, Dict]:
        # Implementation details...
```

## Database Schema

### Audit Logs Table

```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    endpoint VARCHAR(200) NOT NULL,
    method VARCHAR(10) NOT NULL,
    ip_address VARCHAR(100),
    user_agent TEXT,
    device_fingerprint VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_status ON audit_logs(status);
```

### Premium Subscriptions Table

```sql
-- Existing table with new fields
ALTER TABLE premium_subscriptions 
ADD COLUMN platform VARCHAR(50),
ADD COLUMN receipt_data TEXT,
ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();
```

## API Endpoints Implementation

### 1. Premium Status Endpoint

**Route:** `GET /api/premium/status`

**Security Features:**
- Device fingerprint required
- JWT authentication
- Audit logging

**Implementation Pattern:**
```python
@router.get("/status")
async def get_premium_status(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    device_fingerprint: Optional[str] = Header(None, alias="Device-Fingerprint")
):
    # Security check first (outside try-catch)
    if not device_fingerprint:
        AuditService.log(db, user_id=current_user.id, action="premium_status",
                        endpoint=str(request.url.path), method="GET",
                        status="blocked_missing_fingerprint",
                        ip_address=request.client.host,
                        user_agent=request.headers.get("User-Agent"),
                        device_fingerprint=device_fingerprint)
        raise HTTPException(status_code=400, detail="Device fingerprint required")
    
    try:
        # Business logic here
        # ...
    except Exception as e:
        logger.error(f"Error getting premium status for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get premium status")
```

### 2. Receipt Verification Endpoints

**Routes:**
- `POST /api/premium/verify-receipt` (test mode only)
- `POST /api/premium/verify-app-store` (iOS)
- `POST /api/premium/verify-google-play` (Android)

**Security Features:**
- Rate limiting (5/min per user)
- JWT authentication
- Audit logging
- Platform-specific validation

## Environment Configuration

### Development Environment

```bash
# .env.local
PREMIUM_TEST_MODE=true
DATABASE_URL=postgresql://user:password@localhost/bravoball_dev
SECRET_KEY=your_secret_key_here
```

### Production Environment

```bash
# .env.production
PREMIUM_TEST_MODE=false
DATABASE_URL=postgresql://user:password@prod-db/bravoball_prod
SECRET_KEY=your_production_secret_key

# Apple App Store Server API
APPLE_ISSUER_ID=your_apple_issuer_id
APPLE_KEY_ID=your_apple_key_id
APPLE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----

# Google Play Developer API
GOOGLE_PLAY_TOKEN=your_google_play_token
GOOGLE_PACKAGE_NAME=com.bravoball.app
```

## Error Handling Patterns

### 1. Security Exception Handling

**Key Principle:** Security checks must be outside try-catch blocks to prevent 500 errors

```python
# ❌ WRONG - Security exception caught by generic handler
try:
    if not device_fingerprint:
        raise HTTPException(status_code=400, detail="Device fingerprint required")
    # ... business logic
except Exception as e:
    raise HTTPException(status_code=500, detail="Internal error")  # Converts 400 to 500

# ✅ CORRECT - Security checks outside try-catch
if not device_fingerprint:
    raise HTTPException(status_code=400, detail="Device fingerprint required")

try:
    # ... business logic
except Exception as e:
    raise HTTPException(status_code=500, detail="Internal error")
```

### 2. Audit Logging Pattern

**Always log security events before raising exceptions:**

```python
# Log the security event
AuditService.log(
    db,
    user_id=current_user.id,
    action="verify_receipt",
    endpoint=str(request.url.path),
    method="POST",
    status="rate_limited",  # or "blocked_missing_fingerprint", etc.
    ip_address=request.client.host,
    user_agent=request.headers.get("User-Agent"),
    device_fingerprint=device_fingerprint
)

# Then raise the appropriate exception
raise HTTPException(status_code=429, detail="Too many requests")
```

## Testing Implementation

### 1. Unit Tests

**Location:** `tests/services/`

```python
# tests/services/test_rate_limiter.py
def test_rate_limiter_allow():
    limiter = RateLimiter()
    user_id = 1
    endpoint = "/api/premium/verify-receipt"
    
    # First 5 requests should be allowed
    for i in range(5):
        assert limiter.allow(user_id, endpoint, limit=5, window_seconds=60) == True
    
    # 6th request should be blocked
    assert limiter.allow(user_id, endpoint, limit=5, window_seconds=60) == False
```

### 2. Integration Tests

**Location:** `tests/routers/`

```python
# tests/routers/test_premium_security.py
def test_device_fingerprint_enforcement(client, auth_headers):
    # Test without fingerprint
    response = client.get("/api/premium/status", headers=auth_headers)
    assert response.status_code == 400
    
    # Test with fingerprint
    headers = auth_headers.copy()
    headers["Device-Fingerprint"] = "test_device_123"
    response = client.get("/api/premium/status", headers=headers)
    assert response.status_code == 200
```

### 3. End-to-End Tests

**Location:** `scripts/`

```python
# scripts/security_integration_test.py
def test_complete_security_flow():
    # 1. Authenticate
    token = authenticate_user()
    
    # 2. Test device fingerprint
    test_device_fingerprint(token)
    
    # 3. Test rate limiting
    test_rate_limiting(token)
    
    # 4. Test receipt validation
    test_receipt_validation(token)
    
    # 5. Verify audit logs
    verify_audit_logs()
```

## Deployment Considerations

### 1. Rate Limiter Scaling

**Current Implementation:** In-memory (single instance)

**Production Recommendation:** Redis-based rate limiter

```python
# services/redis_rate_limiter.py
import redis
import json

class RedisRateLimiter:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    def allow(self, user_id: int, endpoint: str, limit: int, window_seconds: int) -> bool:
        key = f"rate_limit:{user_id}:{endpoint}"
        current = self.redis.get(key)
        
        if current is None:
            self.redis.setex(key, window_seconds, 1)
            return True
        
        count = int(current)
        if count < limit:
            self.redis.incr(key)
            return True
        
        return False
```

### 2. Audit Log Management

**Log Rotation:**
```bash
# /etc/logrotate.d/bravoball-audit
/var/log/bravoball/audit.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 www-data www-data
}
```

**Database Cleanup:**
```sql
-- Keep audit logs for 1 year
DELETE FROM audit_logs WHERE created_at < NOW() - INTERVAL '1 year';
```

### 3. Monitoring and Alerting

**Key Metrics to Monitor:**
- Rate limiting events per minute
- Failed authentication attempts
- Audit log volume
- Response times for security endpoints

**Alert Thresholds:**
- Rate limiting events > 100/minute
- Failed auth attempts > 50/minute
- Response time > 500ms for security endpoints

## Security Best Practices

### 1. Input Validation

```python
# Validate device fingerprint format
def validate_device_fingerprint(fingerprint: str) -> bool:
    if not fingerprint or len(fingerprint) < 10:
        return False
    # Add additional validation as needed
    return True
```

### 2. Rate Limiting Configuration

```python
# Different limits for different endpoints
RATE_LIMITS = {
    "/api/premium/status": {"limit": 10, "window": 60},
    "/api/premium/verify-receipt": {"limit": 5, "window": 60},
    "/api/premium/validate": {"limit": 5, "window": 60},
}
```

### 3. Audit Log Security

```python
# Sanitize sensitive data before logging
def sanitize_for_audit(data: Dict) -> Dict:
    sensitive_fields = ["password", "token", "receipt_data"]
    sanitized = data.copy()
    for field in sensitive_fields:
        if field in sanitized:
            sanitized[field] = "[REDACTED]"
    return sanitized
```

## Troubleshooting Guide

### Common Issues

1. **500 errors instead of 400/429**
   - **Cause:** Security exceptions caught by generic handler
   - **Solution:** Move security checks outside try-catch blocks

2. **Rate limiter not working across instances**
   - **Cause:** In-memory rate limiter
   - **Solution:** Implement Redis-based rate limiter

3. **Audit logs missing**
   - **Cause:** Database connection issues or transaction rollback
   - **Solution:** Ensure audit logging happens before any potential rollback

4. **Device fingerprint not enforced**
   - **Cause:** Header name mismatch
   - **Solution:** Verify header name is "Device-Fingerprint" (case-sensitive)

### Debug Commands

```bash
# Check audit logs
psql -d bravoball -c "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 10;"

# Check rate limiter state (if using Redis)
redis-cli KEYS "rate_limit:*"

# Monitor API requests
tail -f /var/log/bravoball/api.log | grep "premium"
```

## Performance Optimization

### 1. Database Optimization

```sql
-- Add composite indexes for common queries
CREATE INDEX idx_audit_logs_user_action_time 
ON audit_logs(user_id, action, created_at);

-- Partition audit logs by date for large volumes
CREATE TABLE audit_logs_2025_08 PARTITION OF audit_logs
FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');
```

### 2. Caching Strategy

```python
# Cache user subscription status
@lru_cache(maxsize=1000)
def get_user_subscription_status(user_id: int) -> Dict:
    # Implementation...
```

### 3. Async Processing

```python
# Async audit logging for high-volume scenarios
async def log_audit_event_async(audit_data: Dict):
    # Queue audit event for async processing
    await audit_queue.put(audit_data)
```

---

**Document Control**
- **Created:** August 21, 2025
- **Last Modified:** August 21, 2025
- **Next Review:** September 21, 2025
- **Version:** 1.0
