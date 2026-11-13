import requests
from bs4 import BeautifulSoup
import argparse
from urllib.parse import urlparse, parse_qs
from jinja2 import Environment, FileSystemLoader, select_autoescape
import json
import time

# --- CONFIGURATION ---
SQLI_PAYLOADS = [
    "' OR 1=1 --", 
    "' OR 'a'='a", 
    "\" OR 1=1 --",
    "admin' --"
]

XSS_PAYLOADS = [
    "&lt;script&gt;alert('XSS')&lt;/script&gt;",
    "'"&gt;&lt;script&gt;alert(1)&lt;/script&gt;",
    "\" onmouseover=\"alert(1)\""
]

# --- DATA STRUCTURE ---
class Finding:
    """Structure to hold details of a single vulnerability found."""
    def __init__(self, type, description, severity, details=None):
        self.type = type
        self.description = description
        self.severity = severity
        self.details = details if details else {}

    def to_dict(self):
        return {
            'type': self.type,
            'description': self.description,
            'severity': self.severity,
            'details': self.details
        }

# --- CORE SCANNING FUNCTIONS ---

def check_sqli(url, param_name, base_url, findings_list):
    """Tests a specific parameter for SQL Injection."""
    print(f"  -&gt; Testing SQLi on parameter: {param_name}")

    test_url = base_url
    is_vulnerable = False

    for payload in SQLI_PAYLOADS:
        try:
            # Extract current parameters to build the injection test URL
            current_params = parse_qs(base_url.split('?')[1] if '?' in base_url else '{}')

            # Inject the payload into the target parameter
            test_params = current_params.copy()
            test_params[param_name] = [payload]

            # Rebuild the URL with injected parameters
            test_url = f"{base_url.split('?')[0]}?" + "&amp;".join([f"{k}={v[0]}" for k, v in test_params.items()])

            response = requests.get(test_url, timeout=10)

            # Heuristic check: Checking for error messages or high content length change
            if "SQL syntax" in response.text or len(response.text) &gt; 5000:
                is_vulnerable = True
                print(f"  [!!!] VULNERABLE: {param_name} triggered SQL Error/Anomaly.")
                break
        except requests.exceptions.RequestException as e:
            print(f"  [!] Error during SQLi test: {e}")

    if is_vulnerable:
        findings_list.append(Finding(
            type="SQL Injection",
            description=f"Potential SQL Injection found in parameter '{param_name}'.",
            severity="High",
            details={"parameter": param_name, "test_url": test_url}
        ))

def check_xss(url, input_field_id, base_url, findings_list):
    """Tests a specific input field for Cross-Site Scripting."""
    print(f"  -&gt; Testing XSS on input field ID: {input_field_id}")

    is_vulnerable = False
    for payload in XSS_PAYLOADS:
        try:
            # Simulate submission by adding payload as query parameter for simplicity
            params = parse_qs(base_url.split('?')[1] if '?' in base_url else '{}')
            params['input'] = [payload]

            test_url = f"{base_url.split('?')[0]}?" + "&amp;".join([f"{k}={v[0]}" for k, v in params.items()])
            response = requests.get(test_url, timeout=10)

            # Heuristic check: Checking for script tag reflection in the page body
            if "&lt;script&gt;alert('XSS')&lt;/script&gt;" in response.text:
                 is_vulnerable = True
                 print(f"  [!!!] VULNERABLE: XSS detected via input field {input_field_id}. Payload reflected.")
                 break

        except requests.exceptions.RequestException as e:
            print(f"  [!] Error during XSS test: {e}")

    if is_vulnerable:
        findings_list.append(Finding(
            type="Cross-Site Scripting (XSS)",
            description=f"Potential XSS vulnerability found via input field '{input_field_id}'.",
            severity="Medium",
            details={"field_id": input_field_id, "test_url": url}
        ))


def scan_website(target_url: str):
    """Main function to crawl and test the target website."""
    print("-" * 50)
    print(f"🚀 STARTING SCAN on: {target_url}")
    print("-" * 50)

    findings = []

    try:
        # Initial fetch
        initial_response = requests.get(target_url, timeout=15)
        initial_response.raise_for_status()
        soup = BeautifulSoup(initial_response.content, 'html.parser')

        # --- 1. Scan URL Parameters (GET Injection) ---
        parsed_url = urlparse(target_url)
        query_params = parse_qs(parsed_url.query)
        print(f"\n[ANALYSIS] Found {len(query_params)} potential GET parameters.")
        for param_name in query_params:
            # Use the URL structure as the base for injection testing
            check_sqli(target_url, param_name, target_url, findings)

        # --- 2. Scan Form Fields (POST/Input Fields) ---
        form_fields = soup.find_all(['input', 'textarea'])
        print(f"\n[ANALYSIS] Found {len(form_fields)} potential form input fields.")

        # Iterate through fields to test XSS (We use the field's 'id' or 'name' as the identifier)
        for field in form_fields:
            field_id = field.get('id') or field.get('name')
            if field_id:
                print(f"  -- Testing field: {field_id}")
                check_xss(target_url, field_id, target_url, findings)

    except requests.exceptions.RequestException as e:
        print(f"\n[FATAL ERROR] Could not connect to the target site: {e}")

    # --- Return structured findings ---
    return findings

# --- HTML REPORTING ---

def generate_html_report(findings, target_url, output_filename="vulnerability_report.html"):
    """Generates a full HTML report using Jinja2."""

    # Setup Jinja2 environment
    # We assume the template is in the same directory or provided as a string
    template_file = 'report_template.html'
    env = Environment(
        loader=FileSystemLoader('.'), 
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template(template_file)

    # Render the template
    html_output = template.render(
        target_url=target_url,
        total_findings=len(findings),
        findings=findings
    )

    # Save to file
    with open(output_filename, 'w') as f:
        f.write(html_output)

    print("\n" + "#" * 50)
    print(f"✅ REPORT GENERATED SUCCESSFULLY: {output_filename}")
    print("#" * 50)


# --- EXECUTION BLOCK ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="DIG's Automated Web Vulnerability Scanner Framework.",
        epilog="Example: python scanner.py https://example.com/login?user=test"
    )
    parser.add_argument("url", type=str, help="The full URL of the website to scan.")
    parser.add_argument("--output", type=str, default="vulnerability_report.html", help="Name of the output HTML file.")

    args = parser.parse_args()

    # Ensure the URL has a scheme
    if not args.url.startswith('http'):
        args.url = 'http://' + args.url

    # 1. Scan the website to gather findings
    scan_findings = scan_website(args.url)

    # 2. Generate the HTML report
    generate_html_report(scan_findings, args.url, args.output)
