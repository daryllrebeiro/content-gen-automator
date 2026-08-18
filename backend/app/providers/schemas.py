STORY_SCHEMA = {
    "type": "object",
    "properties": {
        "hook": {"type": "string"},
        "central_claim": {"type": "string"},
        "ending": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "purpose": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["purpose", "summary"],
            },
        },
    },
    "required": ["hook", "central_claim", "ending", "scenes"],
}

NARRATION_SCHEMA = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"],
}

VISUAL_SCHEMA = {
    "type": "object",
    "properties": {
        "story_action": {"type": "string"},
        "camera": {"type": "string"},
        "composition": {"type": "string"},
        "transition": {"type": "string"},
        "beats": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "time_range": {"type": "string"},
                    "title": {"type": "string"},
                    "details": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["time_range", "title", "details"],
            },
        },
    },
    "required": ["story_action", "camera", "composition", "transition", "beats"],
}
