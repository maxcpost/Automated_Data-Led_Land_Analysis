#!/usr/bin/env python3

import os
from dotenv import load_dotenv

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Check if the API keys are available
    openai_key = os.environ.get("OPENAI_API_KEY")
    google_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    
    print("OpenAI API Key:", openai_key[:10] + "..." if openai_key else "Not found")
    print("Google Maps API Key:", google_key[:10] + "..." if google_key else "Not found")

if __name__ == "__main__":
    main() 