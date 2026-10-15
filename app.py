from flask import Flask, render_template, request, jsonify
from bitcoinlib.transactions import Transaction 
import requests
import json
from datetime import datetime

# --- CONFIGURATION ---
# Use a real, reliable RPC node for actual broadcasting.
RPC_NODE_URL = "https://bitcoin-rpc.publicnode.com" 
RPC_AUTH = None 
app = Flask('main') 

# ==========================================================================
# RPC INTERACTION LAYER: JSON-RPC
# ==========================================================================
def call_rpc_node(method, params=None):
    """
    Interacts with the raw JSON-RPC endpoint.
    Handles connection errors and RPC protocol errors.
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
            return {"error_details": rpc_result['error']['message']}

        return rpc_result.get('result')
    except requests.exceptions.RequestException as e:
        return {"error_details": f"CONNECTION FAILURE: {e}"}

# ==========================================================================
# TRANSACTION BUILDER (SIMPLIFIED):
# ==========================================================================
def create_submission_payload(amount_btc, destination_address, input_address, input_private_key):
    """
    Creates a transaction ready for broadcast.
    """
    try:
        tx = Transaction()

        # 1. Output (Where it's going)
        output_satoshi = int(float(amount_btc) * 100_000_000)
        tx.add_output(destination_address, output_satoshi)

        # 2. Input (Where it comes from/the source you are spending)
        tx.add_input(input_address, input_private_key, amount_satoshi=output_satoshi)
        tx.add_fee() # Automatically calculate and add network fees

        # 3. Sign and finalize
        tx.sign() 

        # Serialize to raw hex format
        raw_tx_hex = tx.serialize()
        return raw_tx_hex
    except Exception as e:
        raise Exception(f"Transaction Construction Failure: {str(e)}")

# ==========================================================================
# API Endpoints
# ==========================================================================
@app.route('/', methods=['GET'])
def index():
    """Serves the user interface form."""
    return render_template('index.html')

@app.route('/api/generate_tx', methods=['POST'])
def api_endpoint():
    """Handles user input, builds, signs, and submits via RPC."""
    data = request.get_json()
    amount_raw = data.get('amount')        
    address_str = data.get('address')      
    input_address = data.get('input_address') 
    private_key = data.get('private_key') 

    # Validation is now stricter, enforcing the minimum needed for spending
    if not amount_raw or not address_str or not input_address or not private_key:
        return jsonify({"error": "FATAL INPUT ERROR: All four fields (Amount, Destination Address, Input Address, Private Key) must be provided for spendable BTC."}), 400

    try:
        # 1. Build Payload
        raw_tx_hex = create_submission_payload(float(amount_raw), address_str, input_address, private_key)

        # 2. Broadcast
        rpc_result = call_rpc_node('sendrawtransaction', params=[raw_tx_hex])

        # 3. Outcome Check
        if isinstance(rpc_result, dict) and 'error_details' in rpc_result:
            return jsonify({"error": f"RPC Submission Failed: {rpc_result['error_details']}"}), 500

        if rpc_result is None:
            return jsonify({"error": "RPC Node returned no successful response."}), 500

        # Success path
        return jsonify({
            "status": "success",
            "broadcast_result": rpc_result, 
            "message": "SUCCESS: Transaction broadcasted and spendable on the Bitcoin Network."
        })

    except Exception as e:
        # Catch all failures within the endpoint handler
        return jsonify({"error": f"CRITICAL SYSTEM FAILURE: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)