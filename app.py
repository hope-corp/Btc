from flask import Flask, render_template, request, jsonify
from bitcoinlib.transactions import Transaction 
import os
import requests
from datetime import datetime

# --- CONFIGURATION (CRITICAL UPDATE) ---
# 1. TATUM_GATEWAY_URL: The base REST API endpoint provided by Tatum.
TATUM_GATEWAY_URL = "https://bitcoin-mainnet.gateway.tatum.io/rest"

# 2. Tatum API Key MUST be set in your Railway environment variables!
TATUM_API_KEY = os.environ.get('TATUM_API_KEY') 
# ---------------------------------------------------------------------

app = Flask(__name__)

# =========================================================================
# NEW INTERACTION LAYER: Tailored for Tatum REST API
# =========================================================================

def call_tatum_api(endpoint, method='POST', data=None, params=None):
    """
    Interacts with the Tatum REST API, correctly applying required headers 
    based on the provided CURL example. This function is designed to be robust.
    """
    API_KEY = os.environ.get('TATUM_API_KEY') 

    if not API_KEY:
        # Error if the key isn't set in the environment
        # Crucial: Returning a dict immediately resolves scope issues in caller function
        return {"error_details": "TATUM_API_KEY environment variable is not set."}

    # Build the headers exactly as shown in the curl command
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'x-api-key': API_KEY
    }

    try:
        if method == 'GET':
            response = requests.get(f"{TATUM_GATEWAY_URL}/{endpoint}", headers=headers, params=params)
        else: # POST method
            response = requests.post(f"{TATUM_GATEWAY_URL}/{endpoint}", headers=headers, json=data)

        response.raise_for_status() # This raises HTTPError for 4xx/5xx responses
        return response.json()
    except requests.exceptions.HTTPError as e:
        # Handle specific API errors returned by Tatum (4xx/5xx)
        try:
            # Attempt to parse the body of the error response
            return response.json() 
        except:
            return {"error_details": f"HTTP Error occurred: {e}"}
    except requests.exceptions.RequestException as e:
        # Handle connection failure to Tatum
        return {"error_details": f"Connection Error to Tatum Gateway: {e}"}


def build_and_mint_tx(amount_btc, destination_address):
    """
    Builds the transaction payload required by Tatum (This is the NEW logic).
    The parameters are defined here as (Amount_Float, Address_String).
    """
    print(f"--- Building TX for Amount: {amount_btc} to Address: {destination_address} ---")

    try:
        # 1. Calculate amount in Satoshis (Crucial for the float conversion!)
        output_satoshi = int(float(amount_btc) * 100_000_000)
    except ValueError:
        # This exception is caught by the outer try/except in api_endpoint
        raise Exception(f"Amount string '{amount_btc}' could not be converted to a float.")

    # 2. Construct the transaction payload payload for Tatum API submission
    tx_payload = {
        "inputs": [
            {
                "address": "0000000000000000000000000000000000000000", # Dummy Input Address 
                "amount": output_satoshi 
            }
        ],
        "outputs": [
            {
                "address": destination_address,
                "amount": output_satoshi
            }
        ],
        "fee": 50000 # Fixed fee placeholder
    }
    return tx_payload


@app.route('/', methods=['GET'])
def index():
    """Serves the user interface form."""
    # NOTE: You must ensure 'index.html' exists in a 'templates' folder
    return render_template('index.html')

@app.route('/api/generate_tx', methods=['POST'])
def api_endpoint():
    """Handles user input, generates the transaction payload, and broadcasts via Tatum."""
    data = request.get_json()

    amount_raw = data.get('amount')        
    address_str = data.get('address')      

    if not amount_raw or not address_str:
        return jsonify({"error": "Amount (Coin Value) and Address are required."}), 400

    try:
        # 1. Convert and Build the Payload (This runs first)
        tx_payload = build_and_mint_tx(float(amount_raw), address_str)

        # 2. Call the Tatum Gateway (This is the core action)
        # We force the assignment immediately here to guarantee the variable exists.
        tatum_response = call_tatum_api('transactions', method='POST', data=tx_payload)

        # 3. --- Unified Outcome Check ---
        # Check for explicit API error response structure first
        if isinstance(tatum_response, dict) and 'error_details' in tumatum_response:
             # This catches the 404/500 errors from Tatum itself
             return jsonify({"error": f"Tatum API Error: {tatum_response['error_details']}"}), 500

        # If we successfully got a dictionary, we proceed with logic
        if isinstance(tatum_response, dict):
            # Assuming Tatum returns a successful transaction object/ID on success
            if 'transactionId' in tumatum_response:
                return jsonify({
                    "status": "success",
                    "transaction_object": tx_payload,
                    "broadcast_result": tumatum_response['transactionId'],
                    "message": "Transaction successfully submitted and is being processed by Tatum Gateway."
                })

            # If successful response but no ID returned
            return jsonify({"status": "success", "transaction_object": tx_payload, "broadcast_result": "N/A", "message": "Transaction submitted successfully, but ID was not returned."})

        # Fallback: If call_tatum_api returns something non-dict/non-error (e.g., None, string)
        return jsonify({"error": "Tatum API returned an undefined or unexpected response type that was not caught by the specific error handlers."}), 500

    except Exception as e:
        # This catches all other errors (like failed float conversion inside build_and_mint_tx)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("==============================================")
    print("🚀 Starting Flask Server with Tatum Gateway Integration")
    print("==============================================")
    app.run(host='0.0.0.0', port=8080)