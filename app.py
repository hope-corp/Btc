from flask import Flask, render_template, request, jsonify
from bitcoinlib.transactions import Transaction 
import os
import requests
import json
from datetime import datetime

# --- CONFIGURATION (RPC NODE CHANGE) ---
RPC_NODE_URL = "https://bitcoin-rpc.publicnode.com" 
RPC_AUTH = None 
# -------------------------------------

app = Flask(__name__)

# =========================================================================
# 🧩 RPC INTERACTION LAYER: JSON-RPC
# =========================================================================

def call_rpc_node(method, params=None):
    """
    Interacts with the raw JSON-RPC endpoint using the requests library.
    """
    try:
        rpc_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params if params is not None else [],
            "id": 1 
        }

        response = requests.post(
            RPC_NODE_URL, 
            headers={'Content-Type': 'application/json'}, 
            json=rpc_payload
        )
        response.raise_for_status() 

        rpc_result = response.json()

        if 'error' in rpc_result:
            # RPC protocol error detected
            return {"error_details": rpc_result['error']['message']}

        return rpc_result.get('result')

    except requests.exceptions.RequestException as e:
        # Connection/HTTP failure
        return {"error_details": f"CONNECTION FAILURE: {e}"}


def build_and_mint_tx(amount_btc, destination_address):
    """
    Builds the transaction payload structure (The data blueprint).
    """
    print(f"--- Building TX for Amount: {amount_btc} to Address: {destination_address} ---")
    try:
        output_satoshi = int(float(amount_btc) * 100_000_000)
    except ValueError:
        raise Exception(f"Input amount '{amount_btc}' could not be converted to a float.")

    tx_payload = {
        "inputs": [
            {
                "address": "0000000000000000000000000000000000000000", 
                "amount": output_satoshi 
            }
        ],
        "outputs": [
            {
                "address": destination_address,
                "amount": output_satoshi
            }
        ],
        "fee": 50000 
    }
    return tx_payload

# =========================================================================
# API Endpoints
# =========================================================================

@app.route('/', methods=['GET'])
def index():
    """Serves the user interface form."""
    return render_template('index.html')

@app.route('/api/generate_tx', methods=['POST'])
def api_endpoint():
    """Handles user input, generates the transaction payload, and submits via RPC."""
    data = request.get_json()
    amount_raw = data.get('amount')        
    address_str = data.get('address')      

    if not amount_raw or not address_str:
        return jsonify({"error": "Amount (Coin Value) and Address are required."}), 400

    try:
        # 1. Build the Payload
        tx_payload = build_and_mint_tx(float(amount_raw), address_str)

        # 2. Data Serialization (CRITICAL): 
        # We convert the Python dict to a JSON string. If the RPC node requires raw hex, 
        # this line is the failure point.
        raw_tx_string = json.dumps(tx_payload) 

        # 3. Call the RPC Node
        rpc_result = call_rpc_node('sendrawtransaction', params=[raw_tx_string])

        # 4. Outcome Check
        if isinstance(rpc_result, dict) and 'error_details' in rpc_result:
            return jsonify({"error": f"RPC Submission Failed: {rpc_result['error_details']}"}), 500

        if rpc_result is None:
            return jsonify({"error": "RPC Node returned no successful response."}), 500

        # Success path
        return jsonify({
            "status": "success",
            "transaction_object": tx_payload,
            "broadcast_result": rpc_result, 
            "message": "Transaction successfully submitted to the RPC node. Check the resulting ID on a block explorer."
        })

    except Exception as e:
        # Catch all internal logic failures
        return jsonify({"error": f"System Initialization Failure: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)