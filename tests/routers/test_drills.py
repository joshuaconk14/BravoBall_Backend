"""
Tests for the drills router
"""
import pytest
from fastapi import status
import json

def test_get_all_drills(client, auth_headers, test_drill):
    """Test getting all drills"""
    response = client.get("/drills/", headers=auth_headers)
    
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "drills" in data
    assert isinstance(data["drills"], list)
    assert len(data["drills"]) >= 1
    
    # Check if our test drill is in the results
    drill_ids = [drill["id"] for drill in data["drills"]]
    assert test_drill.id in drill_ids

def test_get_drill_categories(client, auth_headers, test_drill_category):
    """Test getting all drill categories"""
    response = client.get("/drill-categories/", headers=auth_headers)
    
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "categories" in data
    assert isinstance(data["categories"], list)
    assert len(data["categories"]) >= 1
    
    # Check if our test category is in the results
    category_ids = [cat["id"] for cat in data["categories"]]
    assert test_drill_category.id in category_ids
    
def test_filter_drills_by_category(client, auth_headers, test_drill, test_drill_category):
    """Test filtering drills by category"""
    response = client.get(f"/drills/?category={test_drill_category.name}", headers=auth_headers)
    
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "drills" in data
    assert isinstance(data["drills"], list)
    assert len(data["drills"]) >= 1
    
    # All drills should mention the category name
    for drill in data["drills"]:
        assert drill["category"] == test_drill_category.name 