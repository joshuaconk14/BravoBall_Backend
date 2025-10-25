"""
Tests for the drill groups router - testing one endpoint at a time
"""
import pytest
from fastapi import status
import json
from models import Drill, DrillGroup, DrillGroupItem
import uuid

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
    initial_check = client.get(f"/api/drills/{test_drill.uuid}/like", headers=auth_headers)
    assert initial_check.status_code == status.HTTP_200_OK
    assert initial_check.json()["is_liked"] == False
    
    # Like the drill
    like_response = client.post(f"/api/drills/{test_drill.uuid}/like", headers=auth_headers)
    assert like_response.status_code == status.HTTP_200_OK
    assert like_response.json()["is_liked"] == True
    
    # Check that drill is now liked
    check_response = client.get(f"/api/drills/{test_drill.uuid}/like", headers=auth_headers)
    assert check_response.status_code == status.HTTP_200_OK
    assert check_response.json()["is_liked"] == True
    
    # Verify the drill was added to the liked drills group
    liked_drills_response = client.get("/api/liked-drills", headers=auth_headers)
    liked_drills = liked_drills_response.json()["drills"]
    
    assert len(liked_drills) == 1
    # API returns UUIDs as strings
    assert liked_drills[0]["uuid"] == str(test_drill.uuid)

def test_add_multiple_drills_to_group(client, auth_headers, db, test_user, test_drill_category):
    """Test adding multiple drills to a drill group at once"""
    # Create a drill group
    response = client.post(
        "/api/drill-groups",
        json={"name": "Test Group", "description": "Test Description"},
        headers=auth_headers
    )
    assert response.status_code == 200
    group_id = response.json()["id"]
    
    # Create test drills
    drill_uuids = []  # Changed from drill_ids to drill_uuids
    for i in range(3):
        drill = Drill(
            # uuid will be auto-generated by SQLAlchemy
            title=f"Test Drill {i}",
            description=f"Test Description {i}",
            category_id=test_drill_category.id,
            difficulty="beginner",
            video_url=f"https://example.com/video{i}.mp4",
            training_styles=["medium_intensity"],
            type="time_based",
            duration=10,
            intensity="medium",
            equipment=["ball", "cones"],
            suitable_locations=["small_field"],
            instructions=["Step 1", "Step 2"],
            tips=["Tip 1", "Tip 2"],
            common_mistakes=["Mistake 1"],
            progression_steps=["Progress 1"],
            variations=["Variation 1"],
            is_custom=False
        )
        db.add(drill)
        db.commit()
        db.refresh(drill)
        # Convert UUID to string for JSON serialization
        drill_uuids.append(str(drill.uuid))
    
    # Add multiple drills to the group
    response = client.post(
        f"/api/drill-groups/{group_id}/drills",
        json=drill_uuids,  # Send UUIDs as strings
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["added_count"] == 3
    
    # Get the group to verify drills were added
    response = client.get(
        f"/api/drill-groups/{group_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert len(response.json()["drills"]) == 3
    
    # Test adding the same drills again (should skip existing)
    response = client.post(
        f"/api/drill-groups/{group_id}/drills",
        json=drill_uuids,  # Send UUIDs instead of IDs
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["added_count"] == 0  # No new drills added

def test_get_public_drill_groups(client, db, test_user, test_drill_category):
    """Test getting drill groups without authentication"""
    # Create a drill group for the test user
    group = DrillGroup(
        name="Public Test Group",
        description="Public Test Description",
        user_id=test_user.id
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    
    # Create a test drill and add it to the group
    drill = Drill(
        # uuid will be auto-generated by SQLAlchemy
        title="Public Test Drill",
        description="Public Test Description",
        category_id=test_drill_category.id,
        difficulty="beginner",
        video_url="https://example.com/video.mp4",
        training_styles=["medium_intensity"],
        type="time_based",
        duration=10,
        intensity="medium",
        equipment=["ball", "cones"],
        suitable_locations=["small_field"],
        instructions=["Step 1", "Step 2"],
        tips=["Tip 1"],
        common_mistakes=["Mistake 1"],
        progression_steps=["Progress 1"],
        variations=["Variation 1"],
        is_custom=False
    )
    db.add(drill)
    db.commit()
    db.refresh(drill)
    
    # Add drill to group
    drill_item = DrillGroupItem(
        drill_group_id=group.id,
        drill_uuid=drill.uuid,  # Use drill_uuid instead of drill_id
        position=0
    )
    db.add(drill_item)
    db.commit()
    
    # Get the public drill groups
    response = client.get(f"/public/drill-groups?user_id={test_user.id}")
    assert response.status_code == 200
    assert len(response.json()) > 0
    
    # Verify the group we created is in the response
    found = False
    for g in response.json():
        if g["id"] == group.id:
            found = True
            assert g["name"] == "Public Test Group"
            assert len(g["drills"]) == 1
            assert g["drills"][0]["title"] == "Public Test Drill"
    
    assert found, "Created drill group not found in response" 