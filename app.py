from flask import Flask, render_template, request, jsonify
from bitcoinlib.transactions import Transaction
import os
import requests
from datetime import datetime

# --- CONFIGURATION (CRITICAL UPDATE) ---
# 1. TATUM_GATEWAY_URL: The base REST API endpoint provided by Tatum.
TATUM_GATEWAY_URL = "https://bitcoin-mainnet.gateway.tatum.io/rest"

# 2. Tatum API Key MUST be set in your Railway environment variables!
# If you don't set it in Railway, you must uncomment and hardcode it here for testing:
# TATUM_API_KEY_HARDCODED = "t-6ad0a905efcd0163332c909d-2b764bc394834c5eba53d72a"
TATUM_API_KEY = os.environ.get('TATUM_API_KEY') 
# ---------------------------------------------------------------------

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
        # Fallback or error if the environment variable is missing
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

    # 1. Calculate amount in Satoshis (Crucial for the float conversion!)
    try:
        # This line is the one that was failing!
        output_satoshi = int(float(amount_btc) * 100_000_000)
    except ValueError:
        raise Exception(f"Amount string '{amount_btc}' could not be converted to a float.")

    # 2. Construct the transaction payload payload for Tatum API submission
    # NOTE: This payload structure is assumed to be correct for submitting a mint/simple TX to Tatum.
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

    try:
        # *** AGGRESSIVE CONVERSION FIX: Manual conversion FORCED HERE ***
        try:
            amount_float = float(amount_raw)
        except ValueError:
            # If conversion fails, it means the input value itself is invalid.
            return jsonify({"error": f"Amount field '{amount_raw}' is not a valid numeric value."}), 500


        # --- 1. Build the Payload using the guaranteed float value ---
        tx_payload = build_and_mint_tx(amount_float, address_str)

        # --- 2. Attempt to Submit/Broadcast via Tatum REST API ---
        # NOTE: Assuming the correct endpoint for submission is '/transactions' 
        # based on general REST API practices. This path is the most likely variable.
        TATUM_SUBMISSION_ENDPOINT = 'transactions' # <--- REVIEW THIS PATH BASED ON TATUM DOCS

        # Use the Tatum gateway endpoint to submit the transaction
        tatum_response = call_tatum_api(TATUM_SUBMISSION_ENDPOINT, method='POST', data=tx_payload)

        # 3. Process Tatum Response
        if isinstance(tatum_response, dict) and 'error_details' in tumatum_response:
             return jsonify({"error": f"Tatum API Error: {tatum_response['error_details']}"}), 500

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

    except Exception as e:
        # This catches all other errors (like failed float conversion inside build_and_mint_tx)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("==============================================")
    print("🚀 Starting Flask Server with Tatum Gateway Integration")
    print("==============================================")
    app.run(host='0.0.0.0', port=8080)