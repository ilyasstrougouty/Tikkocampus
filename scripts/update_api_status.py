import os
import sys
import json
import requests

# Define the status file location
# This could be in the project root or in a config directory
API_KEY_FILE = "api_keys_status.json"

# Load existing status if the file exists
if os.path.exists(API_KEY_FILE):
    with open(API_KEY_FILE, 'r') as f:
        STATUS = json.load(f)
else:
    STATUS = {}

def call_api(url, headers=None, data=None):
    """
    Helper function to make API requests and handle common error codes.
    """
    try:
        if data:
            response = requests.post(url, headers=headers, json=data, timeout=10)
        else:
            response = requests.get(url, headers=headers, timeout=10)
        
        # Return status code and JSON content
        return response.status_code, response.json()
    except Exception as e:
        return 500, {'error': 'internal_error', 'message': str(e)}

def is_valid_stripe_key_v2(api_key):
    """
    Check if the direct provided Stripe API key is valid using the officially recommended way.
    """
    url = "https://api.stripe.com/v1/accounts"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    status, message = call_api(url, headers)
    # Check if the error is due to authentication
    if status == 200:
        return True, "Success"
    else:
        if message.get('error'):
            return False, f"Stripe API Error: {message['error'].get('message', 'Unknown Error')}"
        else:
            return False, f"Error from Stripe API: {status}"

def is_valid_github_key_v2(api_key):
    """
    Check if the direct provided GitHub API key is valid using the officially recommended way.
    """
    url = "https://api.github.com/user"
    headers = {
        "Authorization": f"token {api_key}",
    }
    
    status, response = call_api(url, headers)
    if status == 200:
        return True, "Success"
    else:
        # Specific error checking for common issues
        if response.get('message') == 'Bad credentials':
            return False, "The GitHub API key provided is invalid."
        else:
            return False, f"GitHub API Error: {response.get('message', 'Unknown Error')}"

def is_valid_openai_key_v2(api_key):
    """
    Check if the direct provided OpenAI API key is valid using the officially recommended way.
    """
    url = "https://api.openai.com/v1/models"
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    
    status, response = call_api(url, headers)
    if status == 200:
        return True, "Success"
    else:
        # Check if the error is due to authentication
        error = response.get('error', {})
        if error.get('code') == 'invalid_api_key':
            return False, "Your provided OpenAI API key is not valid."
        else:
            return False, f"Error from OpenAI API: {error.get('message', 'Unknown Error')}"
        
def is_valid_gemini_key_v2(api_key):
    """
    Check if the direct provided Google Gemini API key is valid using the officially recommended way.
    """
    # Use a safe API call to verify the key
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    status, response = call_api(url)
    if status == 200:
        return True, "Success"
    else:
        # Check for authentication errors
        error = response.get('error', {})
        if error.get('status') == 'UNAUTHENTICATED':
            return False, "Your provided Gemini API key is not valid."
        else:
            return False, f"Error from Gemini API: {error.get('message', 'Unknown Error')}"

def is_valid_anthropic_key_v2(api_key):
    """
    Check if the direct provided Anthropic API key is valid using the officially recommended way.
    """
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    # Minimal data to trigger a key check without a full request
    data = {
        "model": "claude-3-opus-20240229",
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "Hello"}]
    }
    
    status, response = call_api(url, headers, data)
    if status == 200:
        return True, "Success"
    else:
        # Check for authentication errors
        error = response.get('error', {})
        if error.get('type') == 'authentication_error':
            return False, "Your provided Anthropic API key is not valid."
        else:
            # We also accept 400 Bad Request as "key is valid" since it reached the API
            # and the key was accepted before data validation failed.
            if status == 400: return True, "Success"
            return False, f"Error from Anthropic API: {error.get('message', 'Unknown Error')}"

# Helper function to check environment variables and update status
def check_and_update(api_key_name, validator_func):
    api_key = os.getenv(api_key_name)
    if api_key:
        is_valid, message = validator_func(api_key)
        STATUS[api_key_name] = {'valid': is_valid, 'message': message}
    else:
        STATUS[api_key_name] = {'valid': False, 'message': f'{api_key_name} not found in environment variables.'}

def update_all_status():
    VALIDATORS = {
        'STRIPE_API_KEY': is_valid_stripe_key_v2,
        'GITHUB_TOKEN': is_valid_github_key_v2,
        'OPENAI_API_KEY': is_valid_openai_key_v2,
        'GEMINI_API_KEY': is_valid_gemini_key_v2,
        'ANTHROPIC_API_KEY': is_valid_anthropic_key_v2
    }
    
    # Loop over all validators and run each logic
    for api_name, validator in VALIDATORS.items():
        check_and_update(api_name, validator)
    
    # Save the status back to the file
    with open(API_KEY_FILE, 'w') as f:
        json.dump(STATUS, f, indent=4)
        print(f"Status updated in {API_KEY_FILE}")

if __name__ == "__main__":
    update_all_status()
