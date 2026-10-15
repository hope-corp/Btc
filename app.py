from flask import Flask, render_template, request, jsonify
from bitcoinlib.transactions import Transaction 
import os
import requests
from datetime import datetime

# --- CONFIGURATION ---
TATUM_GATEWAY_URL = "https://bitcoin-mainnet.gateway.tatum.io/rest"
# CRITICAL: Ensure this is set in Railway for the full connection to work later
TATUM_API_KEY = os.environ.get('TATUM_API_KEY') 

app = Flask(__name__)

# =========================================================================
# 🧩 CORE LOGIC FUNCTIONS (These prove the math and data structure)
# =========================================================================

def call_tatum_api(endpoint, method='POST', data=None, params=None):
    """
    [RETAINED] This function is the original mechanism for talking to Tatum.
    Used if you re-enable the RPC connection.
    """
    API_KEY = os.environ.get('TATUM_API_KEY') 

    if not API_KEY:
        return {"error_details": "TATUM_API_KEY environment variable is not set."}

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

        response.raise_for_status() # Raises HTTPError for 4xx/5xx
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error_details": f"Connection Error to Tatum Gateway: {e}"}


def build_and_mint_tx(amount_btc, destination_address):
    """
    Builds the transaction payload required by Tatum. 
    This function is the core component to test.
    """
    print(f"--- Building TX for Amount: {amount_btc} to Address: {destination_address} ---")
    try:
        # 1. Calculate amount in Satoshis (Crucial for the float conversion!)
        output_satoshi = int(float(amount_btc) * 100_000_000)
    except ValueError:
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

# =========================================================================
# API Endpoints (The main entry points for the Flask application)
# =========================================================================

@app.route('/', methods=['GET'])
def index():
    """Serves the user interface form."""
    # IMPORTANT: Assumes 'index.html' is in a 'templates' folder
    return render_template('index.html')

@app.route('/api/generate_tx', methods=['POST'])
def api_endpoint():
    """Handles user input, generates the transaction payload LOCALLY and MOCKS success."""
    data = request.get_json()
    amount_raw = data.get('amount')        
    address_str = data.get('address')      

    if not amount_raw or not address_str:
        return jsonify({"error": "Amount (Coin Value) and Address are required."}), 400

    try:
        # 1. Local Conversion Proof & Data Structure Proof
        amount_float = float(amount_raw)

        # 2. Generate Payload LOCALLY
        tx_payload = build_and_mint_tx(amount_float, address_str)

        # 3. MOCKING THE SUCCESS (Bypassing the RPC call for immediate testing)
        mock_success_response = {
            "status": "success",
            "transaction_object": tx_payload,
            "broadcast_result": "MOCK_TX_ID_LOCAL_PROOF_98765", # Hardcoded mock ID
            "message": "SUCCESS (MOCK): Transaction structure generated locally. RPC/Tatum connection ignored for immediate proof. Re-enable call_tatum_api logic to check live connection."
        }
        return jsonify(mock_success_response)

    except Exception as e:
        # Catches any local failure (like failed float conversion inside build_and_mint_tx)
        return jsonify({"error": f"Local Logic Failure: {str(e)}"}), 500

if __name__ == '__main__':
    print("==============================================")
    print("🚀 Starting FLASK SERVER WITH MOCK RPC MODE (Focus on Local Logic)")
    print("==============================================")
    app.run(host='0.0.0.0', port=8080)