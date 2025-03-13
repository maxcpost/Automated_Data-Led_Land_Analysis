#!/usr/bin/env python3

from modules.googledistance.walmart_distance import ensure_api_key

def main():
    # Test ensure_api_key function to check Google Maps API key
    print("Testing ensure_api_key function...")
    api_key = ensure_api_key()
    print("Google Maps API Key:", api_key[:10] + "..." if api_key else "Not found")

if __name__ == "__main__":
    main() 