# """
# This file contains the ProgramGenerator class, which is used to generate a training program for a user based on their onboarding data.
# """

# from typing import List
# from models import OnboardingData, Program, Week
# from config import model
# from langchain_core.messages import SystemMessage, HumanMessage
# import json
# import re

# class ProgramGenerator:
#     def __init__(self):
#         self.weeks_per_chunk = 1  # Generate one week at a time
        
#     async def generate_program(self, data: OnboardingData) -> Program:
#         total_weeks = self._get_total_weeks(data.timeline)
#         weeks = []
#         previous_weeks_context = []

#         for week_num in range(1, total_weeks + 1):
#             prompt = self._create_week_prompt(
#                 data, 
#                 week_num, 
#                 previous_weeks_context
#             )
            
#             week = await self._generate_single_week(prompt, week_num)
#             weeks.append(week)
            
#             # Add summary of this week to context for next iteration
#             previous_weeks_context.append({
#                 "week_number": week.week_number,
#                 "theme": week.theme,
#                 "focus_areas": [drill.type for drill in week.drills]
#             })

#         return Program(
#             weeks=weeks,
#             difficulty=self._determine_difficulty(data),
#             focus_areas=self._extract_focus_areas(weeks)
#         )

#     def _create_week_prompt(self, data: OnboardingData, week_num: int, previous_weeks: list) -> str:
#         previous_context = ""
#         if previous_weeks:
#             previous_context = "Previous weeks' themes:\n" + "\n".join(
#                 f"Week {w['week_number']}: {w['theme']}"
#                 for w in previous_weeks
#             )

#         return f"""You are an expert soccer coach. Create a structured training program for Week {week_num}.
        
#         Player details:
#         - Age Range: {data.ageRange}
#         - Position: {data.position}
#         - Level: {data.level}
#         - Skill Level: {data.skillLevel}
#         - Training Days: {', '.join(data.trainingDays)}
#         - Primary Goal: {data.primaryGoal}
#         - Strengths: {', '.join(data.strengths)}
#         - Areas to Improve: {', '.join(data.weaknesses)}
        
#         {previous_context}

#         Return a JSON object for Week {week_num} with this exact structure, providing specific drills for each training day:
#         {{
#             "week_number": {week_num},
#             "theme": "string",
#             "description": "string",
#             "training_days": [
#                 {{
#                     "day": "Monday",  // Only include specified training days
#                     "focus": "string",  // Primary focus for this day
#                     "total_duration": 90,  // Total minutes for this day
#                     "drills": [
#                         {{
#                             "title": "string",
#                             "description": "string",
#                             "duration": 30,
#                             "type": "string",
#                             "difficulty": "string",
#                             "equipment": ["string"],
#                             "instructions": ["string"],
#                             "tips": ["string"],
#                             "video_url": null
#                         }}
#                     ]
#                 }}
#             ]
#         }}

#         Important:
#         1. Only generate drills for these training days: {', '.join(data.trainingDays)}
#         2. Each day should have 2-3 drills that progressively build on each other
#         3. Total duration per day should be 60-90 minutes
#         4. Focus areas should align with player's goals and weaknesses
#         5. Ensure drill progression makes sense within each day and across the week"""

#     def _get_total_weeks(self, timeline: str) -> int:
#         # Extract number of weeks from timeline string
#         import re
#         match = re.search(r'(\d+)', timeline)
#         return int(match.group(1)) if match else 2  # Default to 2 weeks

#     async def _generate_single_week(self, prompt: str, week_num: int) -> Week:
#         messages = [
#             SystemMessage(content="You are an expert soccer coach. Respond only with valid JSON."),
#             HumanMessage(content=prompt)
#         ]
        
#         try:
#             response = await model.ainvoke(messages)
#             content = response.content
            
#             # Try to extract JSON if it's wrapped in other text
#             json_match = re.search(r'\{[\s\S]*\}', content)
#             if json_match:
#                 content = json_match.group()
            
#             # Parse the JSON
#             week_data = json.loads(content)
            
#             # Validate against Week model
#             return Week.parse_obj(week_data)
            
#         except json.JSONDecodeError as e:
#             print(f"JSON Parsing Error for Week {week_num}: {str(e)}")
#             print(f"Raw Response: {content}")
#             raise ValueError(f"Invalid JSON response from model: {str(e)}")
#         except Exception as e:
#             print(f"Error generating Week {week_num}: {str(e)}")
#             print(f"Raw Response: {content}")
#             raise ValueError(f"Error generating Week {week_num}: {str(e)}")

#     def _determine_difficulty(self, data: OnboardingData) -> str:
#         # Map skill level to appropriate difficulty
#         skill_level_map = {
#             "Beginner": 1,
#             "Intermediate": 2,
#             "Competitive": 3,
#             "Professional": 4
#         }
        
#         # Simplified mapping based on skill level only
#         skill_score = skill_level_map.get(data.skillLevel, 2)
        
#         # Map score to difficulty
#         if skill_score == 1:
#             return "Beginner"
#         elif skill_score == 2:
#             return "Intermediate"
#         elif skill_score == 3:
#             return "Competitive"
#         else:
#             return "Professional"

#     def _extract_focus_areas(self, weeks: List[Week]) -> List[str]:
#         # Collect unique focus areas from all drills across all weeks
#         focus_areas = set()
#         for week in weeks:
#             for drill in week.drills:
#                 focus_areas.add(drill.type)
        
#         # Convert set to sorted list for consistent ordering
#         return sorted(list(focus_areas))