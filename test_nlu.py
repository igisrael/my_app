import os
import json
from dotenv import load_dotenv
load_dotenv()
from chatbot.nlu import extract_intent

result = extract_intent('עידו כהן')
print("JSON RESULT:", json.dumps(result, indent=2, ensure_ascii=False))
