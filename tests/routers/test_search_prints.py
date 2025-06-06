#!/usr/bin/env python
"""
Simple script to test the drill search API and print results.
This bypasses pytest and directly queries the API to show all drill titles.
"""
import sys
import requests
import json
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)

def print_search_results(query: str, results: Dict[str, Any]):
    """Print search results in a clear, simple format"""
    logging.info("\n" + "="*80)
    logging.info(f"SEARCH QUERY: '{query}'")
    logging.info(f"TOTAL RESULTS: {results['total']}")
    logging.info(f"PAGE: {results['page']} of {results['total_pages']}")
    logging.info("="*80)
    
    if not results.get('items'):
        logging.info("NO RESULTS FOUND")
        return
    
    logging.info("\nDRILL TITLES:")
    for i, drill in enumerate(results['items']):
        logging.info(f"{i+1}. {drill['title']} (ID: {drill['id']})")
    
    logging.info("\n" + "="*80)
    logging.info("FULL DETAILS OF FIRST RESULT:")
    if results['items']:
        first_drill = results['items'][0]
        for key, value in first_drill.items():
            if key in ['title', 'description', 'difficulty', 'id']:
                logging.info(f"{key}: {value}")
        
        if 'primary_skill' in first_drill and first_drill['primary_skill']:
            primary_skill = first_drill['primary_skill']
            logging.info(f"primary_skill: {primary_skill.get('category')} - {primary_skill.get('sub_skill')}")
    
    logging.info("="*80)

def test_search(query="", category=None, difficulty=None):
    """Run a search against the API and print results"""
    # Build the URL with query parameters
    base_url = "http://127.0.0.1:8000/public/drills/search"  # Use the public endpoint
    params = []
    
    if query:
        params.append(f"query={query}")
    if category:
        params.append(f"category={category}")
    if difficulty:
        params.append(f"difficulty={difficulty}")
    
    url = base_url
    if params:
        url += "?" + "&".join(params)
    
    logging.info(f"Calling API: {url}")
    
    # Make the request
    try:
        response = requests.get(url)
        
        if response.status_code != 200:
            logging.error(f"Search failed with status {response.status_code}")
            logging.error(f"Response: {response.text}")
            return
        
        data = response.json()
        print_search_results(query or "EMPTY QUERY", data)
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")

if __name__ == "__main__":
    # Process command line arguments
    args = sys.argv[1:]
    
    if not args:
        logging.info("Running tests with various search queries...")
        # Test with empty query
        test_search()
        
        # Test with specific words
        for term in ["drill", "dribbling", "shooting", "practice", "improve"]:
            test_search(query=term)
        
        # Test with categories
        for category in ["dribbling", "shooting"]:
            test_search(category=category)
        
        # Test with difficulties
        for difficulty in ["beginner", "intermediate", "advanced"]:
            test_search(difficulty=difficulty)
        
        # Test with combined filters
        test_search(query="drill", category="dribbling")
        
    else:
        # Use the first argument as search query
        query = args[0]
        category = None
        difficulty = None
        
        if len(args) > 1:
            category = args[1]
        if len(args) > 2:
            difficulty = args[2]
            
        test_search(query, category, difficulty)
        
    logging.info("\nDone!") 