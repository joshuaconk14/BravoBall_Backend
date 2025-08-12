#!/usr/bin/env python3
"""
test_premium.py
Test script for the premium subscription system
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"

def test_premium_system():
    """Test the complete premium subscription system"""
    print("🚀 Testing BravoBall Premium System")
    print("=" * 50)
    
    # Step 1: Login to get access token
    print("\n1. Testing user authentication...")
    login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(f"Response: {login_response.text}")
        return False
    
    login_data = login_response.json()
    access_token = login_data.get("access_token")
    
    if not access_token:
        print("❌ No access token received")
        return False
    
    print("✅ Login successful")
    
    # Headers for authenticated requests
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Device-Fingerprint": "test_device_123",
        "App-Version": "1.0.0"
    }
    
    # Step 2: Test premium status endpoint
    print("\n2. Testing premium status endpoint...")
    status_response = requests.get(f"{BASE_URL}/api/premium/status", headers=headers)
    
    if status_response.status_code != 200:
        print(f"❌ Premium status failed: {status_response.status_code}")
        print(f"Response: {status_response.text}")
        return False
    
    status_data = status_response.json()
    print(f"✅ Premium status: {status_data['data']['status']}")
    print(f"   Plan: {status_data['data']['plan']}")
    print(f"   Features: {len(status_data['data']['features'])}")
    
    # Step 3: Test feature access check
    print("\n3. Testing feature access check...")
    feature_response = requests.post(f"{BASE_URL}/api/premium/check-feature", 
                                   headers=headers,
                                   json={"feature": "unlimitedCustomDrills"})
    
    if feature_response.status_code != 200:
        print(f"❌ Feature access check failed: {feature_response.status_code}")
        return False
    
    feature_data = feature_response.json()
    print(f"✅ Feature access: {feature_data['data']['canAccess']}")
    print(f"   Limit: {feature_data['data']['limit']}")
    
    # Step 4: Test usage tracking
    print("\n4. Testing usage tracking...")
    usage_response = requests.post(f"{BASE_URL}/api/premium/track-usage",
                                 headers=headers,
                                 json={
                                     "featureType": "custom_drill",
                                     "usageDate": datetime.now().isoformat(),
                                     "metadata": {"drillType": "passing", "difficulty": "intermediate"}
                                 })
    
    if usage_response.status_code != 200:
        print(f"❌ Usage tracking failed: {usage_response.status_code}")
        return False
    
    print("✅ Usage tracked successfully")
    
    # Step 5: Test usage stats
    print("\n5. Testing usage statistics...")
    stats_response = requests.get(f"{BASE_URL}/api/premium/usage-stats", headers=headers)
    
    if stats_response.status_code != 200:
        print(f"❌ Usage stats failed: {stats_response.status_code}")
        return False
    
    stats_data = stats_response.json()
    print(f"✅ Usage stats retrieved")
    print(f"   Custom drills used: {stats_data['data']['customDrillsUsed']}")
    print(f"   Sessions used: {stats_data['data']['sessionsUsed']}")
    
    # Step 6: Test subscription upgrade (test endpoint)
    print("\n6. Testing subscription upgrade...")
    upgrade_response = requests.post(f"{BASE_URL}/api/premium/test/set-status",
                                   headers=headers,
                                   params={"status": "premium", "plan": "yearly"})
    
    if upgrade_response.status_code != 200:
        print(f"❌ Subscription upgrade failed: {upgrade_response.status_code}")
        return False
    
    print("✅ Subscription upgraded to premium")
    
    # Step 7: Verify premium status after upgrade
    print("\n7. Verifying premium status after upgrade...")
    time.sleep(1)  # Small delay to ensure database update
    
    status_response = requests.get(f"{BASE_URL}/api/premium/status", headers=headers)
    if status_response.status_code == 200:
        status_data = status_response.json()
        print(f"✅ New status: {status_data['data']['status']}")
        print(f"   New plan: {status_data['data']['plan']}")
        print(f"   Features: {len(status_data['data']['features'])}")
    
    # Step 8: Test premium feature access
    print("\n8. Testing premium feature access...")
    feature_response = requests.post(f"{BASE_URL}/api/premium/check-feature", 
                                   headers=headers,
                                   json={"feature": "unlimitedCustomDrills"})
    
    if feature_response.status_code == 200:
        feature_data = feature_response.json()
        print(f"✅ Premium feature access: {feature_data['data']['canAccess']}")
        print(f"   Limit: {feature_data['data']['limit']}")
    
    # Step 9: Test subscription details
    print("\n9. Testing subscription details...")
    details_response = requests.get(f"{BASE_URL}/api/premium/subscription-details", headers=headers)
    
    if details_response.status_code == 200:
        details_data = details_response.json()
        print(f"✅ Subscription details retrieved")
        print(f"   ID: {details_data['data']['id']}")
        print(f"   Status: {details_data['data']['status']}")
        print(f"   Plan: {details_data['data']['plan']}")
    
    # Step 10: Test subscription cancellation
    print("\n10. Testing subscription cancellation...")
    cancel_response = requests.post(f"{BASE_URL}/api/premium/cancel", headers=headers)
    
    if cancel_response.status_code == 200:
        print("✅ Subscription cancelled successfully")
    
    # Step 11: Verify status after cancellation
    print("\n11. Verifying status after cancellation...")
    time.sleep(1)
    
    status_response = requests.get(f"{BASE_URL}/api/premium/status", headers=headers)
    if status_response.status_code == 200:
        status_data = status_response.json()
        print(f"✅ Final status: {status_data['data']['status']}")
    
    print("\n" + "=" * 50)
    print("🎉 Premium system test completed successfully!")
    return True

def test_receipt_verification():
    """Test receipt verification endpoints"""
    print("\n🧾 Testing receipt verification...")
    
    # Login first
    login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    
    if login_response.status_code != 200:
        print("❌ Login failed for receipt verification test")
        return False
    
    access_token = login_response.json().get("access_token")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Test iOS receipt verification
    print("   Testing iOS receipt verification...")
    ios_response = requests.post(f"{BASE_URL}/api/premium/verify-app-store",
                               headers=headers,
                               json={
                                   "platform": "ios",
                                   "receiptData": "test_receipt_data_ios",
                                   "productId": "bravoball_premium_yearly",
                                   "transactionId": "test_transaction_123"
                               })
    
    if ios_response.status_code == 200:
        print("   ✅ iOS receipt verification successful")
    else:
        print(f"   ❌ iOS receipt verification failed: {ios_response.status_code}")
    
    # Test Android receipt verification
    print("   Testing Android receipt verification...")
    android_response = requests.post(f"{BASE_URL}/api/premium/verify-google-play",
                                   headers=headers,
                                   json={
                                       "platform": "android",
                                       "receiptData": "test_receipt_data_android",
                                       "productId": "bravoball_premium_yearly",
                                       "transactionId": "test_transaction_456"
                                   })
    
    if android_response.status_code == 200:
        print("   ✅ Android receipt verification successful")
    else:
        print(f"   ❌ Android receipt verification failed: {android_response.status_code}")

if __name__ == "__main__":
    try:
        # Test the main premium system
        success = test_premium_system()
        
        if success:
            # Test receipt verification
            test_receipt_verification()
        
        print("\n✨ All tests completed!")
        
    except Exception as e:
        print(f"\n💥 Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
