#!/usr/bin/env python3

import os
import sys
from modules.webui.dashboard import call_openai_api

def main():
    # First ensure dotenv is loaded
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("Environment variables loaded from .env file")
    except ImportError:
        print("python-dotenv not installed, using system environment variables")
    
    # Check API keys directly
    openai_key = os.environ.get("OPENAI_API_KEY")
    google_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    
    print("OpenAI API Key:", openai_key[:10] + "..." if openai_key else "Not found")
    print("Google Maps API Key:", google_key[:10] + "..." if google_key else "Not found")
    
    # Test call_openai_api function to check OpenAI API key
    print("\nTesting call_openai_api with a simple prompt...")
    try:
        response = call_openai_api("Test prompt. Please respond with 'API key working correctly.'")
        print("OpenAI API response:", response[:50] + "..." if len(response) > 50 else response)
    except Exception as e:
        print("Error calling OpenAI API:", str(e))
    
    print("\nEnvironment variables test completed.")

if __name__ == "__main__":
    main() 