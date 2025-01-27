from utils.drill_factory import DrillBuilder

# Using DrillBuilder
sample_drills = [
    DrillBuilder("Wall Pass Mastery")
        .with_description("Rapid fire passing against a wall to improve first touch and passing accuracy")
        .with_type("TIME_BASED")
        .with_duration(10)
        .with_sets(3)
        .with_reps(0)  # Time-based drill
        .with_equipment("BALL", "WALL")
        .with_suitable_locations("INDOOR_COURT", "SMALL_FIELD")
        .with_intensity("medium")
        .with_training_styles("MEDIUM_INTENSITY", "HIGH_INTENSITY")
        .with_difficulty("beginner")
        .with_skills("short_passing", "first_touch")
        .with_instructions(
            "Stand 3-5 meters from wall",
            "Pass ball against wall",
            "Control returning ball with first touch",
            "Pass again as quickly as possible while maintaining control"
        )
        .with_tips(
            "Keep ball close to ground",
            "Use inside of foot for accuracy",
            "Stay on balls of feet"
        )
        .with_variations(
            "Alternate feet",
            "One-touch passing",
            "Add movement between passes"
        )
        .with_rest(60)
        .build(),
        
    DrillBuilder("Power Shot Development")
        .with_description("Focus on generating maximum power while maintaining accuracy")
        .with_type("REP_BASED")
        .with_duration(15)
        .with_sets(4)
        .with_reps(5)
        .with_equipment("BALL", "GOALS")
        .with_suitable_locations("FIELD_WITH_GOALS")
        .with_intensity("high")
        .with_training_styles("HIGH_INTENSITY", "GAME_PREP")
        .with_difficulty("intermediate")
        .with_skills("power_shots", "shooting_technique")
        .with_instructions(
            "Place ball 20 yards from goal",
            "Take 3-step run up",
            "Strike through ball with laces",
            "Aim for corners of goal"
        )
        .with_tips(
            "Lock ankle when striking",
            "Follow through towards target",
            "Plant foot beside ball"
        )
        .with_rest(60)
        .build(),

    DrillBuilder("Cone ZigZag Sprint")
        .with_description("High-speed dribbling through cones with acceleration focus")
        .with_type("SET_BASED")
        .with_duration(12)
        .with_sets(4)
        .with_reps(2)
        .with_equipment("BALL", "CONES")
        .with_suitable_locations("SMALL_FIELD", "INDOOR_COURT")
        .with_intensity("high")
        .with_training_styles("HIGH_INTENSITY", "GAME_PREP")
        .with_difficulty("advanced")
        .with_skills("speed_dribbling", "close_control")
        .with_instructions(
            "Set up 6 cones in zigzag pattern, 2 meters apart",
            "Start with ball at first cone",
            "Dribble through cones at maximum speed",
            "Sprint back to start with ball"
        )
        .with_tips(
            "Use both feet",
            "Keep head up",
            "Touch ball with every step"
        )
        .with_rest(60)  # 60 seconds rest between sets
        .build()
]

