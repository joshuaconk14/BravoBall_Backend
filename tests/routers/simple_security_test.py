#!/usr/bin/env python3
"""
simple_security_test.py
Simple integration test for core security features
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"

def get_token():
    """Get auth token"""
    response = requests.post(f"{BASE_URL}/login/", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    return response.json().get("access_token")

def test_basic_premium_status():
    """Test basic premium status with device fingerprint"""
    print("🔍 Testing basic premium status...")
    
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Device-Fingerprint": "test_device_123"
    }
    
    response = requests.get(f"{BASE_URL}/api/premium/status", headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Premium status: {data.get('data', {}).get('status')}")
        return True
    else:
        print(f"   Error: {response.text}")
        return False

def test_device_fingerprint_block():
    """Test device fingerprint blocking"""
    print("🔐 Testing device fingerprint blocking...")
    
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}"
        # No Device-Fingerprint header
    }
    
    response = requests.get(f"{BASE_URL}/api/premium/status", headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 400:
        print("   ✅ Correctly blocked without device fingerprint")
        return True
    else:
        print(f"   ❌ Expected 400, got {response.status_code}")
        return False

def test_receipt_verification():
    """Test receipt verification"""
    print("🧾 Testing receipt verification...")
    
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Device-Fingerprint": "test_device_123"
    }
    
    # Test iOS
    response = requests.post(f"{BASE_URL}/api/premium/verify-app-store", 
                           headers=headers,
                           json={
                               "platform": "ios",
                               "receiptData": "test_receipt",
                               "productId": "bravoball_premium_yearly",
                               "transactionId": "test_transaction"
                           })
    
    print(f"   iOS Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            print("   ✅ iOS receipt verification working")
            return True
    
    print(f"   ❌ iOS receipt verification failed: {response.text}")
    return False

def test_rate_limiting():
    """Test rate limiting"""
    print("⏱️ Testing rate limiting...")
    
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Device-Fingerprint": "test_device_123"
    }
    
    # Make 6 requests quickly
    success_count = 0
    rate_limited_count = 0
    
    for i in range(6):
        response = requests.post(f"{BASE_URL}/api/premium/verify-receipt", 
                               headers=headers,
                               json={
                                   "platform": "ios",
                                   "receiptData": f"rate_test_{i}",
                                   "productId": "bravoball_premium_yearly",
                                   "transactionId": f"rate_test_{i}"
                               })
        
        if response.status_code == 200:
            success_count += 1
        elif response.status_code == 429:
            rate_limited_count += 1
            print(f"   Request {i+1}: Rate limited ✅")
        else:
            print(f"   Request {i+1}: Status {response.status_code}")
    
    print(f"   Successful: {success_count}, Rate limited: {rate_limited_count}")
    
    if rate_limited_count > 0:
        print("   ✅ Rate limiting working")
        return True
    else:
        print("   ❌ Rate limiting not working")
        return False

def main():
    print("🔒 Simple Security Features Test")
    print("=" * 40)
    
    tests = [
        ("Basic Premium Status", test_basic_premium_status),
        ("Device Fingerprint Block", test_device_fingerprint_block),
        ("Receipt Verification", test_receipt_verification),
        ("Rate Limiting", test_rate_limiting),
    ]
    
    passed = 0
    for name, test_func in tests:
        print(f"\n{name}:")
        if test_func():
            passed += 1
            print(f"✅ {name} PASSED")
        else:
            print(f"❌ {name} FAILED")
    
    print(f"\n📊 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All core security features working!")
    else:
        print("⚠️ Some features need attention")

if __name__ == "__main__":
    main()
