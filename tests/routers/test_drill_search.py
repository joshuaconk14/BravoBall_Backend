"""
Tests for the drill search functionality
This test file helps diagnose issues with the search endpoint by running various search queries
and displaying detailed results.

Command to run test:

pytest tests/routers/test_drill_search.py -v

or 

python test_search_prints.py
"""
import pytest
from fastapi import status
import json
import re
import sys
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from models import Drill, DrillCategory, DrillSkillFocus

def create_test_drills(db: Session, num_drills: int = 10):
    """Create a variety of test drills with different titles, descriptions, and categories"""
    # Create some categories first
    categories = {
        "dribbling": "Drills focusing on dribbling skills",
        "shooting": "Drills focusing on shooting skills",
        "passing": "Drills focusing on passing skills",
        "first_touch": "Drills focusing on first touch skills",
        "fitness": "Drills focusing on fitness"
    }
    
    category_objs = {}
    for name, desc in categories.items():
        cat = db.query(DrillCategory).filter(DrillCategory.name == name).first()
        if not cat:
            cat = DrillCategory(name=name, description=desc)
            db.add(cat)
            db.commit()
            db.refresh(cat)
        category_objs[name] = cat
    
    # Create some test drills with varied titles and descriptions
    test_drills = [
        {
            "title": "Cone Dribbling Drill",
            "description": "A drill to practice tight dribbling through cones",
            "category": "dribbling",
            "difficulty": "beginner",
            "primary_skill": {"category": "dribbling", "sub_skill": "close_control"}
        },
        {
            "title": "Shooting Practice",
            "description": "Improve your shooting accuracy with this drill",
            "category": "shooting",
            "difficulty": "intermediate",
            "primary_skill": {"category": "shooting", "sub_skill": "accuracy"}
        },
        {
            "title": "Passing Triangle",
            "description": "A drill for working on quick passes with teammates",
            "category": "passing",
            "difficulty": "beginner",
            "primary_skill": {"category": "passing", "sub_skill": "short_passing"}
        },
        {
            "title": "First Touch Control",
            "description": "Improve your ball control with this first touch drill",
            "category": "first_touch",
            "difficulty": "beginner",
            "primary_skill": {"category": "first_touch", "sub_skill": "ground_control"}
        },
        {
            "title": "Agility Ladder Drill",
            "description": "Improve your footwork and agility",
            "category": "fitness",
            "difficulty": "intermediate",
            "primary_skill": {"category": "fitness", "sub_skill": "agility"}
        },
        {
            "title": "Advanced Dribbling Moves",
            "description": "Learn advanced dribbling techniques",
            "category": "dribbling",
            "difficulty": "advanced",
            "primary_skill": {"category": "dribbling", "sub_skill": "ball_mastery"}
        },
        {
            "title": "Power Shooting Drill",
            "description": "Improve the power behind your shots",
            "category": "shooting",
            "difficulty": "intermediate",
            "primary_skill": {"category": "shooting", "sub_skill": "power"}
        },
        {
            "title": "Wall Pass Drill",
            "description": "Practice quick wall passes to improve your passing game",
            "category": "passing",
            "difficulty": "intermediate",
            "primary_skill": {"category": "passing", "sub_skill": "wall_passing"}
        },
        {
            "title": "Aerial Control Practice",
            "description": "Improve your control of the ball from the air",
            "category": "first_touch",
            "difficulty": "advanced",
            "primary_skill": {"category": "first_touch", "sub_skill": "aerial_control"}
        },
        {
            "title": "Endurance Training",
            "description": "Build your stamina for the full game",
            "category": "fitness",
            "difficulty": "advanced",
            "primary_skill": {"category": "fitness", "sub_skill": "endurance"}
        }
    ]
    
    # Only create as many as requested
    drills_to_create = test_drills[:num_drills]
    
    created_drills = []
    for drill_data in drills_to_create:
        # Create the drill
        drill = Drill(
            title=drill_data["title"],
            description=drill_data["description"],
            category_id=category_objs[drill_data["category"]].id,
            duration=10,
            intensity="medium",
            training_styles=["medium_intensity"],
            type="time_based",
            sets=None,
            reps=None,
            rest=None,
            equipment=["ball", "cones"],
            suitable_locations=["small_field", "backyard"],
            difficulty=drill_data["difficulty"],
            instructions=["Step 1", "Step 2"],
            tips=["Tip 1", "Tip 2"],
            common_mistakes=["Mistake 1"],
            progression_steps=["Progress 1"],
            variations=["Variation 1"],
            video_url=None,
            thumbnail_url=None
        )
        db.add(drill)
        db.commit()
        db.refresh(drill)
        
        # Add primary skill focus
        primary_skill = DrillSkillFocus(
            drill_id=drill.id,
            category=drill_data["primary_skill"]["category"],
            sub_skill=drill_data["primary_skill"]["sub_skill"],
            is_primary=True
        )
        db.add(primary_skill)
        db.commit()
        
        created_drills.append(drill)
    
    return created_drills

def print_search_results(query: str, results: Dict[str, Any], highlight: bool = True):
    """Print search results in a detailed format to help diagnose search issues"""
    print("\n" + "="*80)
    print(f"SEARCH QUERY: '{query}'")
    print(f"TOTAL RESULTS: {results['total']}")
    print(f"PAGE: {results['page']} of {results['total_pages']}")
    print("="*80)
    
    if not results['items']:
        print("NO RESULTS FOUND")
        return
    
    for i, drill in enumerate(results['items']):
        title = drill['title']
        description = drill['description']
        
        # Highlight the matched text if requested
        if highlight and query:
            # Case insensitive highlight
            pattern = re.compile(re.escape(query), re.IGNORECASE)
            title = pattern.sub(lambda m: f"\033[1;31m{m.group(0)}\033[0m", title)
            description = pattern.sub(lambda m: f"\033[1;31m{m.group(0)}\033[0m", description)
        
        print(f"\n{i+1}. {title}")
        print(f"   ID: {drill['id']}")
        print(f"   Description: {description}")
        if 'primary_skill' in drill and drill['primary_skill']:
            primary_skill = drill['primary_skill']
            print(f"   Primary Skill: {primary_skill.get('category', 'N/A')} - {primary_skill.get('sub_skill', 'N/A')}")
        print(f"   Difficulty: {drill.get('difficulty', 'N/A')}")
    
    print("\n" + "="*80)

def test_search_drills_empty_query(client, auth_headers, db):
    """Test searching with an empty query (should return all drills)"""
    # First create some test drills
    test_drills = create_test_drills(db)
    
    # Search with empty query
    response = client.get("/api/drills/search", headers=auth_headers)
    
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    
    print_search_results("", data)
    
    # Empty query should return all drills (up to the limit)
    assert data["total"] >= len(test_drills)

def test_search_drills_by_title(client, auth_headers, db):
    """Test searching for drills by title"""
    # Create test drills
    create_test_drills(db)
    
    # Terms to search for
    search_terms = ["Dribbling", "Shooting", "drill", "practice"]
    
    for term in search_terms:
        response = client.get(f"/api/drills/search?query={term}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        print_search_results(term, data)
        
        # Check if the search term is in the title or description of all results
        for drill in data["items"]:
            term_in_title = term.lower() in drill["title"].lower()
            term_in_desc = term.lower() in drill["description"].lower()
            assert term_in_title or term_in_desc, f"Search term '{term}' not found in drill title or description"

def test_search_drills_by_description(client, auth_headers, db):
    """Test searching for drills by description"""
    # Create test drills
    create_test_drills(db)
    
    # Terms to search for
    search_terms = ["accuracy", "control", "quick", "improve"]
    
    for term in search_terms:
        response = client.get(f"/api/drills/search?query={term}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        print_search_results(term, data)
        
        # For descriptive terms, we'll just check that we have some results
        if data["total"] > 0:
            has_drill_with_term = any(
                term.lower() in drill["title"].lower() or 
                term.lower() in drill["description"].lower() 
                for drill in data["items"]
            )
            assert has_drill_with_term, f"Search term '{term}' not found in any drill title or description"

def test_search_drills_by_category(client, auth_headers, db):
    """Test searching for drills by category"""
    # Create test drills
    create_test_drills(db)
    
    # Categories to search for
    categories = ["dribbling", "shooting", "passing", "first_touch", "fitness"]
    
    for category in categories:
        response = client.get(f"/api/drills/search?category={category}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        print_search_results(f"Category: {category}", data, highlight=False)
        
        # Check if all results have the right primary skill category
        assert all(
            (
                drill.get("primary_skill", {}).get("category", "").lower() == category.lower() or
                # Some drills might have it in secondary skills
                any(
                    skill.get("category", "").lower() == category.lower() 
                    for skill in drill.get("secondary_skills", [])
                )
            )
            for drill in data["items"]
        ), f"Some drills do not match category '{category}'"

def test_search_drills_by_difficulty(client, auth_headers, db):
    """Test searching for drills by difficulty level"""
    # Create test drills
    create_test_drills(db)
    
    # Difficulty levels to search for
    difficulties = ["beginner", "intermediate", "advanced"]
    
    for difficulty in difficulties:
        response = client.get(f"/api/drills/search?difficulty={difficulty}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        print_search_results(f"Difficulty: {difficulty}", data, highlight=False)
        
        # Check if all results have the right difficulty
        assert all(
            drill.get("difficulty", "").lower() == difficulty.lower()
            for drill in data["items"]
        ), f"Some drills do not match difficulty '{difficulty}'"

def test_search_drills_combined_filters(client, auth_headers, db):
    """Test searching for drills with combined filters"""
    # Create test drills
    create_test_drills(db)
    
    # Combined search parameters
    search_params = [
        {"query": "drill", "category": "dribbling"},
        {"query": "improve", "difficulty": "beginner"},
        {"query": "practice", "category": "shooting", "difficulty": "intermediate"}
    ]
    
    for params in search_params:
        # Build query URL
        query_parts = []
        for key, value in params.items():
            query_parts.append(f"{key}={value}")
        query_string = "&".join(query_parts)
        
        response = client.get(f"/api/drills/search?{query_string}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        print_search_results(f"Combined: {query_string}", data, highlight=False)
        
        # Check if results match all criteria
        for drill in data["items"]:
            # Check query match
            if "query" in params:
                term = params["query"].lower()
                term_in_title = term in drill["title"].lower()
                term_in_desc = term in drill["description"].lower()
                assert term_in_title or term_in_desc, f"Search term '{term}' not found in drill title or description"
            
            # Check category match
            if "category" in params:
                category = params["category"].lower()
                has_category = (
                    drill.get("primary_skill", {}).get("category", "").lower() == category or
                    any(
                        skill.get("category", "").lower() == category
                        for skill in drill.get("secondary_skills", [])
                    )
                )
                assert has_category, f"Drill does not have category '{category}'"
            
            # Check difficulty match
            if "difficulty" in params:
                difficulty = params["difficulty"].lower()
                assert drill.get("difficulty", "").lower() == difficulty, f"Drill does not have difficulty '{difficulty}'"

if __name__ == "__main__":
    # This allows running this file directly (without pytest) for debugging
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from main import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    
    # You'll need to authenticate:
    # 1. Login to get token
    login_response = client.post("/api/login", json={
        "email": "your-email@example.com",
        "password": "your-password"
    })
    
    if login_response.status_code != 200:
        print("Authentication failed. Update your credentials.")
        sys.exit(1)
    
    token = login_response.json()["token"]
    auth_headers = {"Authorization": f"Bearer {token}"}
    
    # Test a simple search
    search_term = "dribbling"  # Change this to test different searches
    response = client.get(f"/api/drills/search?query={search_term}", headers=auth_headers)
    
    if response.status_code != 200:
        print(f"Search failed with status {response.status_code}: {response.text}")
        sys.exit(1)
    
    data = response.json()
    print_search_results(search_term, data) 