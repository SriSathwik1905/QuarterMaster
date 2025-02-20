import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    print("API Key found:", api_key)
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content("Say hello")
    print("Gemini Response:", response.text)
else:
    print("ERROR: API Key not found. Check your .env file and environment.")
