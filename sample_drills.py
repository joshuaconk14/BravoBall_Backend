from utils.drill_factory import DrillBuilder
from models import (
    SkillCategory, PassingSubSkill, ShootingSubSkill,
    DribblingSubSkill, FirstTouchSubSkill, FitnessSubSkill,
    TrainingLocation, TrainingStyle, Difficulty, Equipment
)

# Using DrillBuilder to create one drill per subcategory
sample_drills = [
    # PASSING DRILLS
    DrillBuilder("Quick Short Pass Combinations")
        .with_description("Quick-fire passing between partners to improve short passing accuracy")
        .with_type("TIME_BASED")
        .with_duration(15)
        .with_sets(4)
        .with_reps(0)
        .with_equipment(Equipment.BALL.value)
        .with_suitable_locations(TrainingLocation.SMALL_FIELD.value, TrainingLocation.INDOOR_COURT.value)
        .with_intensity("medium")
        .with_training_styles(TrainingStyle.MEDIUM_INTENSITY.value)
        .with_difficulty(Difficulty.BEGINNER.value)
        .with_primary_skill(SkillCategory.PASSING, PassingSubSkill.SHORT_PASSING)
        .with_secondary_skills(
            (SkillCategory.FIRST_TOUCH, FirstTouchSubSkill.GROUND_CONTROL),
            (SkillCategory.FITNESS, FitnessSubSkill.AGILITY)
        )
        .with_instructions(
            "Position 5 yards apart",
            "Pass and move in triangular pattern",
            "One-touch passing when possible"
        )
        .with_tips(
            "Keep passes on ground",
            "Use inside of foot",
            "Maintain good body position"
        )
        .with_rest(30)
        .build(),

    DrillBuilder("Long Range Switch Play")
        .with_description("Practice switching play with long diagonal passes")
        .with_type("REP_BASED")
        .with_duration(20)
        .with_sets(3)
        .with_reps(10)
        .with_equipment(Equipment.BALL.value, Equipment.CONES.value)
        .with_suitable_locations(TrainingLocation.FULL_FIELD.value)
        .with_intensity("high")
        .with_training_styles(TrainingStyle.GAME_PREP.value)
        .with_difficulty(Difficulty.ADVANCED.value)
        .with_primary_skill(SkillCategory.PASSING, PassingSubSkill.LONG_PASSING)
        .with_secondary_skills(
            (SkillCategory.FIRST_TOUCH, FirstTouchSubSkill.AERIAL_CONTROL)
        )
        .with_instructions(
            "Set up two 10-yard zones on opposite flanks",
            "Switch play between zones",
            "Receiver controls and returns"
        )
        .with_tips(
            "Strike through ball with laces",
            "Follow through towards target",
            "Communicate with receiver"
        )
        .with_rest(45)
        .build(),

    DrillBuilder("Wall Pass Mastery")
        .with_description("Rapid fire passing against a wall to improve passing accuracy")
        .with_type("TIME_BASED")
        .with_duration(10)
        .with_sets(3)
        .with_reps(0)
        .with_equipment(Equipment.BALL.value, Equipment.WALL.value)
        .with_suitable_locations(TrainingLocation.INDOOR_COURT.value)
        .with_intensity("medium")
        .with_training_styles(TrainingStyle.MEDIUM_INTENSITY.value)
        .with_difficulty(Difficulty.INTERMEDIATE.value)
        .with_primary_skill(SkillCategory.PASSING, PassingSubSkill.WALL_PASSING)
        .with_secondary_skills(
            (SkillCategory.FIRST_TOUCH, FirstTouchSubSkill.ONE_TOUCH_CONTROL),
            (SkillCategory.FITNESS, FitnessSubSkill.AGILITY)
        )
        .with_instructions(
            "Stand 5 yards from wall",
            "Pass against wall continuously",
            "Control and pass quickly"
        )
        .with_tips(
            "Vary power and angle",
            "Stay on toes",
            "Use both feet"
        )
        .with_rest(30)
        .build(),

    # SHOOTING DRILLS
    DrillBuilder("Power Shot Training")
        .with_description("Focus on generating maximum power in shots")
        .with_type("REP_BASED")
        .with_duration(25)
        .with_sets(4)
        .with_reps(5)
        .with_equipment(Equipment.BALL.value, Equipment.GOALS.value)
        .with_suitable_locations(TrainingLocation.FULL_FIELD.value)
        .with_intensity("high")
        .with_training_styles(TrainingStyle.HIGH_INTENSITY.value)
        .with_difficulty(Difficulty.INTERMEDIATE.value)
        .with_primary_skill(SkillCategory.SHOOTING, ShootingSubSkill.POWER)
        .with_secondary_skills(
            (SkillCategory.SHOOTING, ShootingSubSkill.LONG_SHOTS)
        )
        .with_instructions(
            "Place ball 20 yards from goal",
            "Generate power through technique",
            "Aim for corners"
        )
        .with_tips(
            "Lock ankle",
            "Strike ball cleanly",
            "Follow through"
        )
        .with_rest(45)
        .build(),

    DrillBuilder("Clinical Finishing")
        .with_description("Close range finishing drills to improve accuracy")
        .with_type("REP_BASED")
        .with_duration(20)
        .with_sets(3)
        .with_reps(8)
        .with_equipment(Equipment.BALL.value, Equipment.GOALS.value)
        .with_suitable_locations(TrainingLocation.FULL_FIELD.value)
        .with_intensity("medium")
        .with_training_styles(TrainingStyle.GAME_PREP.value)
        .with_difficulty(Difficulty.BEGINNER.value)
        .with_primary_skill(SkillCategory.SHOOTING, ShootingSubSkill.FINISHING)
        .with_secondary_skills(
            (SkillCategory.FIRST_TOUCH, FirstTouchSubSkill.GROUND_CONTROL),
            (SkillCategory.DRIBBLING, DribblingSubSkill.CLOSE_CONTROL)
        )
        .with_instructions(
            "Set up 12 yards from goal",
            "Receive and finish quickly",
            "Vary finishing techniques"
        )
        .with_tips(
            "Place shots accurately",
            "Keep head steady",
            "Pick spot before shooting"
        )
        .with_rest(30)
        .build(),

    DrillBuilder("Volley Practice")
        .with_description("Improve technique for volleying the ball")
        .with_type("REP_BASED")
        .with_duration(15)
        .with_sets(4)
        .with_reps(6)
        .with_equipment(Equipment.BALL.value, Equipment.GOALS.value)
        .with_suitable_locations(TrainingLocation.FULL_FIELD.value)
        .with_intensity("medium")
        .with_training_styles(TrainingStyle.MEDIUM_INTENSITY.value)
        .with_difficulty(Difficulty.ADVANCED.value)
        .with_primary_skill(SkillCategory.SHOOTING, ShootingSubSkill.VOLLEYS)
        .with_secondary_skills(
            (SkillCategory.FIRST_TOUCH, FirstTouchSubSkill.AERIAL_CONTROL),
            (SkillCategory.FITNESS, FitnessSubSkill.AGILITY)
        )
        .with_instructions(
            "Partner tosses ball",
            "Strike volley at goal",
            "Vary height and angle"
        )
        .with_tips(
            "Watch ball onto foot",
            "Keep body over ball",
            "Time jump correctly"
        )
        .with_rest(40)
        .build(),

    DrillBuilder("Long Range Accuracy")
        .with_description("Practice shooting accurately from distance")
        .with_type("REP_BASED")
        .with_duration(25)
        .with_sets(3)
        .with_reps(7)
        .with_equipment(Equipment.BALL.value, Equipment.GOALS.value, Equipment.CONES.value)
        .with_suitable_locations(TrainingLocation.FULL_FIELD.value)
        .with_intensity("high")
        .with_training_styles(TrainingStyle.GAME_PREP.value)
        .with_difficulty(Difficulty.ADVANCED.value)
        .with_primary_skill(SkillCategory.SHOOTING, ShootingSubSkill.LONG_SHOTS)
        .with_secondary_skills(
            (SkillCategory.SHOOTING, ShootingSubSkill.POWER)
        )
        .with_instructions(
            "Set up 25 yards from goal",
            "Aim for specific targets",
            "Focus on technique first"
        )
        .with_tips(
            "Strike through ball cleanly",
            "Keep shot down",
            "Follow through to target"
        )
        .with_rest(45)
        .build(),

    # DRIBBLING DRILLS
    DrillBuilder("Ball Mastery Circuit")
        .with_description("Fundamental ball control exercises")
        .with_type("TIME_BASED")
        .with_duration(15)
        .with_sets(3)
        .with_reps(0)
        .with_equipment(Equipment.BALL.value, Equipment.CONES.value)
        .with_suitable_locations(TrainingLocation.SMALL_FIELD.value, TrainingLocation.INDOOR_COURT.value)
        .with_intensity("low")
        .with_training_styles(TrainingStyle.MEDIUM_INTENSITY.value)
        .with_difficulty(Difficulty.BEGINNER.value)
        .with_primary_skill(SkillCategory.DRIBBLING, DribblingSubSkill.BALL_MASTERY)
        .with_secondary_skills(
            (SkillCategory.FIRST_TOUCH, FirstTouchSubSkill.GROUND_CONTROL),
            (SkillCategory.FITNESS, FitnessSubSkill.AGILITY)
        )
        .with_instructions(
            "Perform various touches",
            "Inside/outside rolls",
            "Figure 8s through legs"
        )
        .with_tips(
            "Keep ball close",
            "Use both feet",
            "Stay balanced"
        )
        .with_rest(30)
        .build(),

    DrillBuilder("Tight Space Control")
        .with_description("Improve close control in confined spaces")
        .with_type("TIME_BASED")
        .with_duration(12)
        .with_sets(4)
        .with_reps(0)
        .with_equipment(Equipment.BALL.value, Equipment.CONES.value)
        .with_suitable_locations(TrainingLocation.SMALL_FIELD.value, TrainingLocation.INDOOR_COURT.value)
        .with_intensity("medium")
        .with_training_styles(TrainingStyle.MEDIUM_INTENSITY.value)
        .with_difficulty(Difficulty.INTERMEDIATE.value)
        .with_primary_skill(SkillCategory.DRIBBLING, DribblingSubSkill.CLOSE_CONTROL)
        .with_secondary_skills(
            (SkillCategory.DRIBBLING, DribblingSubSkill.BALL_MASTERY),
            (SkillCategory.FITNESS, FitnessSubSkill.AGILITY)
        )
        .with_instructions(
            "Create 3x3 yard box",
            "Dribble within space",
            "Respond to commands"
        )
        .with_tips(
            "Quick small touches",
            "Keep head up",
            "Use all parts of feet"
        )
        .with_rest(30)
        .build(),

    DrillBuilder("Speed Dribbling Course")
        .with_description("High-speed dribbling with directional changes")
        .with_type("TIME_BASED")
        .with_duration(15)
        .with_sets(4)
        .with_reps(0)
        .with_equipment(Equipment.BALL.value, Equipment.CONES.value)
        .with_suitable_locations(TrainingLocation.SMALL_FIELD.value, TrainingLocation.INDOOR_COURT.value)
        .with_intensity("high")
        .with_training_styles(TrainingStyle.HIGH_INTENSITY.value)
        .with_difficulty(Difficulty.ADVANCED.value)
        .with_primary_skill(SkillCategory.DRIBBLING, DribblingSubSkill.SPEED_DRIBBLING)
        .with_secondary_skills(
            (SkillCategory.FITNESS, FitnessSubSkill.SPEED),
            (SkillCategory.FITNESS, FitnessSubSkill.AGILITY)
        )
        .with_instructions(
            "Set up cone course",
            "Dribble at pace",
            "Change direction quickly"
        )
        .with_tips(
            "Push ball ahead",
            "Stay on toes",
            "Use both feet"
        )
        .with_rest(45)
        .build(),

    DrillBuilder("1v1 Skills Training")
        .with_description("Practice moves to beat defenders")
        .with_type("REP_BASED")
        .with_duration(20)
        .with_sets(3)
        .with_reps(6)
        .with_equipment(Equipment.BALL.value, Equipment.CONES.value)
        .with_suitable_locations(TrainingLocation.SMALL_FIELD.value)
        .with_intensity("high")
        .with_training_styles(TrainingStyle.GAME_PREP.value)
        .with_difficulty(Difficulty.ADVANCED.value)
        .with_primary_skill(SkillCategory.DRIBBLING, DribblingSubSkill.ONE_V_ONE_MOVES)
        .with_secondary_skills(
            (SkillCategory.DRIBBLING, DribblingSubSkill.CLOSE_CONTROL),
            (SkillCategory.FITNESS, FitnessSubSkill.AGILITY)
        )
        .with_instructions(
            "Practice specific moves",
            "Execute against defender",
            "Accelerate after move"
        )
        .with_tips(
            "Sell the fake",
            "Change pace",
            "Keep ball protected"
        )
        .with_rest(40)
        .build(),

    # FIRST TOUCH DRILLS
    DrillBuilder("Ground Control Basics")
        .with_description("Improve control of ground passes")
        .with_type("TIME_BASED")
        .with_duration(15)
        .with_sets(3)
        .with_reps(0)
        .with_equipment(Equipment.BALL.value)
        .with_suitable_locations(TrainingLocation.SMALL_FIELD.value, TrainingLocation.INDOOR_COURT.value)
        .with_intensity("low")
        .with_training_styles(TrainingStyle.MEDIUM_INTENSITY.value)
        .with_difficulty(Difficulty.BEGINNER.value)
        .with_primary_skill(SkillCategory.FIRST_TOUCH, FirstTouchSubSkill.GROUND_CONTROL)
        .with_secondary_skills(
            (SkillCategory.PASSING, PassingSubSkill.SHORT_PASSING),
            (SkillCategory.DRIBBLING, DribblingSubSkill.CLOSE_CONTROL)
        )
        .with_instructions(
            "Receive ground passes",
            "Control into space",
            "Maintain fluid motion"
        )
        .with_tips(
            "Cushion the ball",
            "Open body position",
            "Look before receiving"
        )
        .with_rest(30)
        .build(),

    DrillBuilder("Aerial Control Practice")
        .with_description("Develop control of aerial balls")
        .with_type("REP_BASED")
        .with_duration(20)
        .with_sets(4)
        .with_reps(8)
        .with_equipment(Equipment.BALL.value)
        .with_suitable_locations(TrainingLocation.SMALL_FIELD.value, TrainingLocation.INDOOR_COURT.value)
        .with_intensity("medium")
        .with_training_styles(TrainingStyle.GAME_PREP.value)
        .with_difficulty(Difficulty.ADVANCED.value)
        .with_primary_skill(SkillCategory.FIRST_TOUCH, FirstTouchSubSkill.AERIAL_CONTROL)
        .with_secondary_skills(
            (SkillCategory.FIRST_TOUCH, FirstTouchSubSkill.GROUND_CONTROL),
            (SkillCategory.FITNESS, FitnessSubSkill.AGILITY)
        )
        .with_instructions(
            "Partner serves high balls",
            "Control with different surfaces",
            "Keep ball close"
        )
        .with_tips(
            "Watch ball all the way",
            "Relax receiving surface",
            "Prepare next action"
        )
        .with_rest(40)
        .build(),

    DrillBuilder("Turn and Face")
        .with_description("Practice turning with the ball under control")
        .with_type("TIME_BASED")
        .with_duration(15)
        .with_sets(3)
        .with_reps(0)
        .with_equipment(Equipment.BALL.value, Equipment.CONES.value)
        .with_suitable_locations(TrainingLocation.SMALL_FIELD.value, TrainingLocation.INDOOR_COURT.value)
        .with_intensity("medium")
        .with_training_styles(TrainingStyle.MEDIUM_INTENSITY.value)
        .with_difficulty(Difficulty.INTERMEDIATE.value)
        .with_primary_skill(SkillCategory.FIRST_TOUCH, FirstTouchSubSkill.TURNING_WITH_BALL)
        .with_secondary_skills(
            (SkillCategory.DRIBBLING, DribblingSubSkill.CLOSE_CONTROL),
            (SkillCategory.FITNESS, FitnessSubSkill.AGILITY)
        )
        .with_instructions(
            "Receive with back to goal",
            "Turn quickly",
            "Accelerate into space"
        )
        .with_tips(
            "Check shoulder",
            "Use first touch to turn",
            "Keep ball close"
        )
        .with_rest(30)
        .build(),

    DrillBuilder("One Touch Control")
        .with_description("Develop instant control and redistribution")
        .with_type("TIME_BASED")
        .with_duration(15)
        .with_sets(4)
        .with_reps(0)
        .with_equipment(Equipment.BALL.value)
        .with_suitable_locations(TrainingLocation.SMALL_FIELD.value, TrainingLocation.INDOOR_COURT.value)
        .with_intensity("high")
        .with_training_styles(TrainingStyle.HIGH_INTENSITY.value)
        .with_difficulty(Difficulty.ADVANCED.value)
        .with_primary_skill(SkillCategory.FIRST_TOUCH, FirstTouchSubSkill.ONE_TOUCH_CONTROL)
        .with_secondary_skills(
            (SkillCategory.PASSING, PassingSubSkill.SHORT_PASSING),
            (SkillCategory.FITNESS, FitnessSubSkill.AGILITY)
        )
        .with_instructions(
            "One touch passing sequence",
            "Vary pace and direction",
            "Keep ball moving"
        )
        .with_tips(
            "Stay on toes",
            "Open body shape",
            "Look before ball arrives"
        )
        .with_rest(45)
        .build(),

    # FITNESS DRILLS
    DrillBuilder("Speed Development")
        .with_description("Improve acceleration and top speed")
        .with_type("SET_BASED")
        .with_duration(20)
        .with_sets(5)
        .with_reps(4)
        .with_equipment(Equipment.CONES.value)
        .with_suitable_locations(TrainingLocation.SMALL_FIELD.value, TrainingLocation.INDOOR_COURT.value)
        .with_intensity("high")
        .with_training_styles(TrainingStyle.HIGH_INTENSITY.value)
        .with_difficulty(Difficulty.INTERMEDIATE.value)
        .with_primary_skill(SkillCategory.FITNESS, FitnessSubSkill.SPEED)
        .with_secondary_skills(
            (SkillCategory.FITNESS, FitnessSubSkill.AGILITY),
            (SkillCategory.FITNESS, FitnessSubSkill.ENDURANCE)
        )
        .with_instructions(
            "Sprint intervals",
            "Focus on technique",
            "Full recovery between sets"
        )
        .with_tips(
            "Drive arms",
            "Stay on toes",
            "Maintain form"
        )
        .with_rest(60)
        .build(),

    DrillBuilder("Agility Circuit")
        .with_description("Improve quickness and change of direction")
        .with_type("TIME_BASED")
        .with_duration(15)
        .with_sets(4)
        .with_reps(0)
        .with_equipment(Equipment.CONES.value)
        .with_suitable_locations(TrainingLocation.SMALL_FIELD.value, TrainingLocation.INDOOR_COURT.value)
        .with_intensity("high")
        .with_training_styles(TrainingStyle.HIGH_INTENSITY.value)
        .with_difficulty(Difficulty.INTERMEDIATE.value)
        .with_primary_skill(SkillCategory.FITNESS, FitnessSubSkill.AGILITY)
        .with_secondary_skills(
            (SkillCategory.FITNESS, FitnessSubSkill.SPEED),
            (SkillCategory.FITNESS, FitnessSubSkill.ENDURANCE)
        )
        .with_instructions(
            "Complete agility course",
            "Quick direction changes",
            "Maintain speed throughout"
        )
        .with_tips(
            "Stay low",
            "Quick feet",
            "Sharp turns"
        )
        .with_rest(45)
        .build(),

    DrillBuilder("Endurance Builder")
        .with_description("Build stamina and aerobic capacity")
        .with_type("TIME_BASED")
        .with_duration(30)
        .with_sets(2)
        .with_reps(0)
        .with_equipment(Equipment.CONES.value)
        .with_suitable_locations(TrainingLocation.SMALL_FIELD.value, TrainingLocation.FULL_FIELD.value)
        .with_intensity("medium")
        .with_training_styles(TrainingStyle.MEDIUM_INTENSITY.value)
        .with_difficulty(Difficulty.INTERMEDIATE.value)
        .with_primary_skill(SkillCategory.FITNESS, FitnessSubSkill.ENDURANCE)
        .with_secondary_skills(
            (SkillCategory.FITNESS, FitnessSubSkill.SPEED),
            (SkillCategory.FITNESS, FitnessSubSkill.AGILITY)
        )
        .with_instructions(
            "Continuous movement",
            "Vary intensity",
            "Include ball work"
        )
        .with_tips(
            "Pace yourself",
            "Control breathing",
            "Stay hydrated"
        )
        .with_rest(90)
        .build(),
]

