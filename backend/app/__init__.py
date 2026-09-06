# Compatibility shim for google-adk with current google-genai
try:
    import google.genai.types as _genai_types
    if not hasattr(_genai_types, "InteractionStatus"):
        _genai_types.InteractionStatus = str
    if not hasattr(_genai_types, "TranslationConfig"):
        _genai_types.TranslationConfig = dict
except ImportError:
    pass
