"""
Tests for the drill groups router - testing one endpoint at a time
"""
import pytest
from fastapi import status
import json

def test_get_user_drill_groups(client, auth_headers, test_user, test_drill_group):
    """Test getting all drill groups for a user"""
    response = client.get("/api/drill-groups/", headers=auth_headers)
    
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    
    group = response.json()[0]
    assert group["id"] == test_drill_group.id
    assert group["name"] == "Test Group"
    assert group["description"] == "A test drill group"
    assert group["is_liked_group"] == False
    assert isinstance(group["drills"], list)
    assert len(group["drills"]) == 0

def test_get_drill_group_by_id(client, auth_headers, test_drill_group):
    """Test getting a specific drill group by ID"""
    response = client.get(f"/api/drill-groups/{test_drill_group.id}", headers=auth_headers)
    
    assert response.status_code == status.HTTP_200_OK
    
    group = response.json()
    assert group["id"] == test_drill_group.id
    assert group["name"] == "Test Group"
    assert group["description"] == "A test drill group"
    assert group["is_liked_group"] == False
    assert isinstance(group["drills"], list)

def test_create_drill_group(client, auth_headers):
    """Test creating a new drill group"""
    # First, check how many groups exist initially
    initial_response = client.get("/api/drill-groups/", headers=auth_headers)
    initial_count = len(initial_response.json())
    
    # Create a new group
    new_group_data = {
        "name": "My New Group",
        "description": "A newly created drill group",
        "drills": [],
        "is_liked_group": False
    }
    
    response = client.post("/api/drill-groups/", headers=auth_headers, json=new_group_data)
    
    assert response.status_code == status.HTTP_200_OK
    
    created_group = response.json()
    assert created_group["id"] is not None
    assert created_group["name"] == "My New Group"
    assert created_group["description"] == "A newly created drill group"
    assert created_group["is_liked_group"] == False
    assert isinstance(created_group["drills"], list)
    assert len(created_group["drills"]) == 0
    
    # Verify it was actually added by checking all groups
    all_groups_response = client.get("/api/drill-groups/", headers=auth_headers)
    all_groups = all_groups_response.json()
    
    assert len(all_groups) == initial_count + 1  # One more group than before
    assert any(group["name"] == "My New Group" for group in all_groups)

def test_get_liked_drills_group(client, auth_headers):
    """Test getting the liked drills group (creates if needed)"""
    response = client.get("/api/liked-drills", headers=auth_headers)
    
    assert response.status_code == status.HTTP_200_OK
    
    liked_group = response.json()
    assert liked_group["name"] == "Liked Drills"
    assert liked_group["is_liked_group"] == True
    assert isinstance(liked_group["drills"], list)
    
    # The liked group should also appear in the normal drill groups list
    all_groups_response = client.get("/api/drill-groups/", headers=auth_headers)
    all_groups = all_groups_response.json()
    
    liked_groups = [g for g in all_groups if g["is_liked_group"] == True]
    assert len(liked_groups) == 1
    assert liked_groups[0]["name"] == "Liked Drills"

def test_like_drill(client, auth_headers, test_drill):
    """Test liking a drill"""
    # Check initial state - drill should not be liked
    initial_check = client.get(f"/api/drills/{test_drill.id}/like", headers=auth_headers)
    assert initial_check.status_code == status.HTTP_200_OK
    assert initial_check.json()["is_liked"] == False
    
    # Like the drill
    like_response = client.post(f"/api/drills/{test_drill.id}/like", headers=auth_headers)
    assert like_response.status_code == status.HTTP_200_OK
    assert like_response.json()["is_liked"] == True
    
    # Check that drill is now liked
    check_response = client.get(f"/api/drills/{test_drill.id}/like", headers=auth_headers)
    assert check_response.status_code == status.HTTP_200_OK
    assert check_response.json()["is_liked"] == True
    
    # Verify the drill was added to the liked drills group
    liked_drills_response = client.get("/api/liked-drills", headers=auth_headers)
    liked_drills = liked_drills_response.json()["drills"]
    
    assert len(liked_drills) == 1
    assert liked_drills[0]["id"] == test_drill.id 