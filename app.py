from flask import Flask, render_template, request, jsonify
from bitcoinlib.transactions import Transaction 
import os
import requests
import json
from datetime import datetime

# --- CONFIGURATION ---
RPC_NODE_URL = "https://bitcoin-rpc.publicnode.com" 
RPC_AUTH = None 
# ----------------------
app = Flask(name)

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
            # RPC protocol error detected
            return {"error_details": rpc_result['error']['message']}

        return rpc_result.get('result')
    except requests.exceptions.RequestException as e:
        # Connection/HTTP failure
        return {"error_details": f"CONNECTION FAILURE: {e}"}

TRANSACTION BUILDING AND SIGNING LOGIC (THE FIX)
def build_and_mint_tx(amount_btc, destination_address, input_address, input_private_key):
    """
    Constructs the TX object, adds outputs, and signs it locally.
    This solves the "TX decode failed" error by providing a cryptographically valid object.
    """
    try:
        # 1. Convert Amount to Satoshis
        output_satoshi = int(float(amount_btc) * 100_000_000)

        # 2. Initialize Transaction Object
        tx = Transaction()

        # 3. Define Outputs (Where the funds go)
        tx.add_output(destination_address, output_satoshi)

        # 4. Define Inputs (Where the funds come from - THE FIX)
        tx.add_input(input_address, input_private_key, amount_satoshi=output_satoshi)

        # 5. Calculate and Add Fees
        tx.add_fee() 

        # 6. Sign the Transaction (Crucial step for validity)
        tx.sign() 

        # 7. Serialize to Raw Hex (What the RPC node demands for sendrawtransaction)
        raw_tx_hex = tx.serialize()

        return {
            "descriptive_payload": tx.to_dict(), 
            "raw_hex": raw_tx_hex
        }
    except Exception as e:
        raise Exception(f"TX Construction/Signing Failure: {str(e)}")
=========================================================================
API Endpoints
=========================================================================
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

    if not amount_raw or not address_str or not input_address or not private_key:
        return jsonify({"error": "Missing Fields Error: Amount, Destination Address, Input Address, AND Private Key are required."}), 400

    try:
        # 1. Build and Sign Locally (The Core Logic)
        tx_data = build_and_mint_tx(float(amount_raw), address_str, input_address, private_key)

        # 2. Call the RPC Node with the raw hex string
        rpc_result = call_rpc_node('sendrawtransaction', params=[tx_data['raw_hex']])

        # 3. Outcome Check
        if isinstance(rpc_result, dict) and 'error_details' in rpc_result:
            return jsonify({"error": f"RPC Submission Failed: {rpc_result['error_details']}"}), 500

        if rpc_result is None:
            return jsonify({"error": "RPC Node returned no successful response."}), 500

        # Success path
        return jsonify({
            "status": "success",
            "transaction_object": tx_data['descriptive_payload'],
            "broadcast_result": rpc_result, 
            "message": "Transaction successfully submitted to the RPC node. Awaiting confirmation on block explorer."
        })

    except Exception as e:
        # Catch all failures
        return jsonify({"error": f"System Initialization Failure: {str(e)}"}), 500
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)