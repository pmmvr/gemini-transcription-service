from google.genai import types

SAFETY_SETTINGS = [
    types.SafetySetting(
        category=types.HarmCategory["HARM_CATEGORY_HATE_SPEECH"],
        threshold=types.HarmBlockThreshold.BLOCK_NONE
    ),
    types.SafetySetting(
        category=types.HarmCategory["HARM_CATEGORY_DANGEROUS_CONTENT"],
        threshold=types.HarmBlockThreshold.BLOCK_NONE
    ),
    types.SafetySetting(
        category=types.HarmCategory["HARM_CATEGORY_SEXUALLY_EXPLICIT"],
        threshold=types.HarmBlockThreshold.BLOCK_NONE
    ),
    types.SafetySetting(
        category=types.HarmCategory["HARM_CATEGORY_HARASSMENT"],
        threshold=types.HarmBlockThreshold.BLOCK_NONE
    ),
]