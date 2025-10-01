# BravoBall Premium Subscription System

## 🎯 Overview

This document describes the implementation of the premium subscription system for BravoBall. The system handles user authentication, subscription management, receipt verification, and premium status validation.

## 🏗️ Architecture

### Database Models

#### PremiumSubscription
- **id**: Primary key
- **user_id**: Foreign key to users table
- **status**: Subscription status (free, premium, trial, expired)
- **plan_type**: Subscription plan (free, monthly, yearly, lifetime)
- **start_date**: When subscription started
- **end_date**: When subscription expires (null for lifetime)
- **trial_end_date**: When trial period ends
- **is_active**: Whether subscription is currently active
- **platform**: Platform (ios, android, web)
- **receipt_data**: Receipt data for validation
- **created_at**: Record creation timestamp
- **updated_at**: Last update timestamp



### API Endpoints

#### Premium Status Management
- `GET /api/premium/status` - Get current premium status
- `POST /api/premium/validate` - Validate premium status
- `GET /api/premium/subscription-details` - Get detailed subscription info

#### Subscription Management
- `POST /api/premium/subscribe` - Subscribe to premium plan
- `POST /api/premium/cancel` - Cancel subscription
- `POST /api/premium/test/set-status` - Test endpoint for status changes

#### Receipt Verification
- `POST /api/premium/verify-receipt` - Generic receipt verification
- `POST /api/premium/verify-app-store` - iOS receipt verification
- `POST /api/premium/verify-google-play` - Android receipt verification

#### Usage Management
- `GET /api/premium/usage-stats` - Get usage statistics
- `POST /api/premium/check-feature` - Check feature access

## 🔐 Premium Features

### Feature Matrix

| Feature | Free | Trial | Premium | Expired |
|---------|------|-------|---------|---------|
| No Ads | ❌ | ✅ | ✅ | ❌ |
| Unlimited Drills | ❌ | ✅ | ✅ | ❌ |
| Unlimited Custom Drills | ❌ | ✅ | ✅ | ❌ |
| Unlimited Sessions | ❌ | ✅ | ✅ | ❌ |
| Advanced Analytics | ❌ | ✅ | ✅ | ❌ |
| Basic Drills | ✅ | ✅ | ✅ | ✅ |
| Weekly Summaries | ✅ | ✅ | ✅ | ❌ |
| Monthly Summaries | ✅ | ✅ | ✅ | ❌ |

### Free Tier Limits

- **Custom Drills**: 3 per month
- **Sessions**: 1 per day

## 🚀 Getting Started

### 1. Database Setup

Run the premium table creation script:

```bash
python create_premium_tables.py
```

This will:
- Create the `premium_subscriptions` table
- Create necessary indexes
- Create default free subscriptions for existing users

### 2. Start the Server

```bash
python main.py
```

Or with uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Test the System

Run the test script:

```bash
python scripts/test_premium.py
```

## 📱 API Usage Examples

### Get Premium Status

```bash
curl -X GET "http://localhost:8000/api/premium/status" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Device-Fingerprint: device_hash_123" \
  -H "App-Version: 1.0.0"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "premium",
    "plan": "yearly",
    "startDate": "2024-01-15T00:00:00Z",
    "endDate": "2025-01-15T00:00:00Z",
    "trialEndDate": null,
    "isActive": true,
    "features": [
      "noAds",
      "unlimitedDrills",
      "unlimitedCustomDrills",
      "unlimitedSessions",
      "advancedAnalytics"
    ]
  }
}
```

### Check Feature Access

```bash
curl -X POST "http://localhost:8000/api/premium/check-feature" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"feature": "unlimitedCustomDrills"}'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "canAccess": true,
    "feature": "unlimitedCustomDrills",
    "remainingUses": null,
    "limit": "unlimited"
  }
}
```

### Upgrade to Premium (Test)

```bash
curl -X POST "http://localhost:8000/api/premium/test/set-status?status=premium&plan=yearly" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 🔧 Configuration

### Environment Variables

The system uses the same database configuration as the main application:

- `DATABASE_URL` - PostgreSQL connection string
- `POSTGRES_PASSWORD` - Database password
- `POSTGRES_USER` - Database username
- `POSTGRES_HOST` - Database host
- `POSTGRES_DB` - Database name

### Premium Features Configuration

Features and their access levels are configured in `services/premium_service.py`:

```python
PREMIUM_FEATURES = {
    "noAds": ["premium", "trial"],
    "unlimitedDrills": ["premium", "trial"],
    "unlimitedCustomDrills": ["premium", "trial"],
    "unlimitedSessions": ["premium", "trial"],
    "advancedAnalytics": ["premium", "trial"],
    "basicDrills": ["free", "premium", "trial", "expired"],
    "weeklySummaries": ["free", "premium", "trial"],
    "monthlySummaries": ["free", "premium", "trial"]
}
```

### Free Tier Limits

```python
FREE_TIER_LIMITS = {
    "custom_drills_per_month": 3,
    "sessions_per_day": 1
}
```

## 🧪 Testing

### Test Endpoints

The system includes test endpoints for development:

- `POST /api/premium/test/set-status` - Set user's premium status
- `POST /api/premium/test/clear-cache` - Clear any cached data
- `POST /api/premium/test/simulate-expiry` - Simulate subscription expiry

### Test Script

The `scripts/test_premium.py` script provides comprehensive testing:

1. User authentication
2. Premium status retrieval
3. Feature access checking
4. Usage tracking
5. Usage statistics
6. Subscription upgrade
7. Premium feature verification
8. Subscription details
9. Subscription cancellation
10. Receipt verification

## 🔒 Security Features

### JWT Authentication
- All premium endpoints require valid JWT tokens
- Tokens are validated on every request

### Device Fingerprinting
- Device fingerprint header required for status requests
- Helps prevent unauthorized access

### Rate Limiting
- Premium validation limited to 5 requests per minute per user
- Implemented in the router logic

### Receipt Verification
- Platform-specific receipt validation
- Server-side verification with platform APIs

## 📊 Monitoring & Analytics

### Usage Tracking
- All premium feature usage is logged
- Metadata stored for analytics
- Monthly and daily limits enforced

### Subscription Analytics
- Status distribution
- Plan type distribution
- Conversion rates
- Active subscription counts

### Logging
- Comprehensive logging for all premium operations
- Error tracking and debugging information
- User action audit trail

## 🚀 Production Deployment

### Receipt Verification
Replace the mock verification in `verify_receipt` with actual platform API calls:

#### iOS (App Store)
```python
# Use App Store Server API
response = await fetch('https://api.storekit.itunes.apple.com/inApps/v1/lookup/{orderId}', {
    method: 'GET',
    headers: {
        'Authorization': f'Bearer {appStoreToken}',
        'User-Agent': 'BravoBall/1.0'
    }
})
```

#### Android (Google Play)
```python
# Use Google Play Developer API
response = await fetch(f'https://www.googleapis.com/androidpublisher/v3/applications/{packageName}/purchases/subscriptions/{subscriptionId}/tokens/{token}', {
    method: 'GET',
    headers: {
        'Authorization': f'Bearer {googlePlayToken}'
    }
})
```

### SSL/TLS
- Ensure all production endpoints use HTTPS
- Valid SSL certificates required

### Database
- Use production-grade PostgreSQL
- Implement proper backup and recovery
- Monitor performance and optimize queries

## 🔄 Maintenance

### Regular Tasks
- Check for expired trials
- Monitor subscription renewals
- Review usage patterns
- Update platform API credentials

### Trial Expiry Check
```python
from services.premium_service import PremiumService

# Check for expired trials
expired_users = PremiumService.check_trial_expiry(db)
```

### Analytics
```python
# Get subscription analytics
analytics = PremiumService.get_subscription_analytics(db)
print(f"Conversion rate: {analytics['conversion_rate']:.2f}%")
```

## 🐛 Troubleshooting

### Common Issues

#### Database Connection
- Verify database credentials
- Check network connectivity
- Ensure database is running

#### JWT Token Issues
- Check token expiration
- Verify token format
- Ensure proper authorization header

#### Premium Status Not Updating
- Check database transactions
- Verify subscription logic
- Review error logs

### Debug Mode

Enable debug logging by setting log level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [App Store Server API](https://developer.apple.com/documentation/appstoreserverapi/)
- [Google Play Developer API](https://developers.google.com/android-publisher)

## 🤝 Contributing

When contributing to the premium system:

1. Follow existing code patterns
2. Add comprehensive tests
3. Update documentation
4. Ensure security best practices
5. Test with multiple user scenarios

## 📞 Support

For issues or questions about the premium system:

1. Check the logs for error details
2. Review this documentation
3. Test with the provided test script
4. Contact the development team

---

**Last Updated**: January 2024
**Version**: 1.0.0
