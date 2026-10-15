from flask import Flask, render_template, request, jsonify
# bitcoinlib is kept for potential internal verification, but Tatum requests are primary
from bitcoinlib.transactions import Transaction 
import os
import requests
from datetime import datetime

# --- CONFIGURATION (CRITICAL UPDATE) ---
# 1. TATUM_GATEWAY_URL: The base REST API endpoint provided by Tatum.
TATUM_GATEWAY_URL = "https://bitcoin-mainnet.gateway.tatum.io/rest"

# 2. Tatum API Key MUST be set in your Railway environment variables!
TATUM_API_KEY = os.environ.get('TATUM_API_KEY') 

app = Flask(__name__)

# =========================================================================
# NEW INTERACTION LAYER: Tailored for Tatum REST API
# =========================================================================

def call_tatum_api(endpoint, method='POST', data=None, params=None):
    """
    Interacts with the Tatum REST API, correctly applying required headers 
    based on the provided CURL example.
    """
    API_KEY = os.environ.get('TATUM_API_KEY') 

    if not API_KEY:
        # Error if the key isn't set in the environment
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
        # If conversion fails here, it means the string was bad.
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
    return render_template('index.html')

@app.route('/api/generate_tx', methods=['POST'])
def api_endpoint():
    """Handles user input, generates the transaction payload, and broadcasts via Tatum."""
    data = request.get_json()

    amount_raw = data.get('amount')        
    address_str = data.get('address')      

    if not amount_raw or not address_str:
        return jsonify({"error": "Amount (Coin Value) and Address are required."}), 400

    # Initialize the response variable defensively to prevent NameError
    tatum_response = None 

    try:
        # 1. Build the Payload (This runs first)
        tx_payload = build_and_mint_tx(float(amount_raw), address_str)

        # 2. Call the Tatum Gateway (This is the core action)
        # NOTE: '/transactions' is the endpoint being called. If this fails, this path is wrong.
        tatum_response = call_tatum_api('transactions', method='POST', data=tx_payload)

        # 3. --- Defensive Check and Execution (The fix for 'name not defined') ---
        if isinstance(tatum_response, dict) and 'error_details' in tumatum_response:
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

        # Fallback if call_tatum_api returned something unexpected (like None)
        return jsonify({"error": "Tatum API returned an undefined or unexpected response type."}), 500

    except Exception as e:
        # This catches all other errors (like failed float conversion inside build_and_mint_tx)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("==============================================")
    print("🚀 Starting Flask Server with Tatum Gateway Integration")
    print("==============================================")
    app.run(host='0.0.0.0', port=8080)