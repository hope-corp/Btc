
from flask import Flask, render_template, request, jsonify
from bitcoinlib.transactions import Transaction 
import requests
import json
from datetime import datetime

# --- CONFIGURATION ---
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

        # Check for protocol errors returned by the node itself
        if 'error' in rpc_result:
            return {"error_details": rpc_result['error']['message']}

        return rpc_result.get('result')
    except requests.exceptions.RequestException as e:
        # Catch general connection or HTTP errors
        return {"error_details": f"CONNECTION FAILURE: {e}"}

# ==========================================================================
# TRANSACTION BUILDER (SIMPLIFIED):
# ==========================================================================
def create_submission_payload(amount_btc, destination_address, input_address, input_private_key):
    """
    Creates a dictionary payload optimized for direct RPC submission.
    """
    try:
        # Initialize the transaction object
        tx = Transaction()

        # Define and add the output address
        output_satoshi = int(float(amount_btc) * 100_000_000)
        tx.add_output(destination_address, output_satoshi)

        # --- CRITICAL FIX: FALLBACK LOGIC FOR SIMPLIFIED FRONTEND ---
        # If the frontend only sends Amount/Address, we assume defaults for the missing inputs.
        default_input_address = "MANUAL_INPUT_ADDRESS_TO_FALLBACK" 
        default_private_key = "MANUAL_FALLBACK_PRIVATE_KEY_TO_AUTHORIZE" 

        # Use the provided data, or the fallback data if inputs are empty
        final_input_address = input_address if input_address else default_input_address
        final_private_key = input_private_key if input_private_key else default_private_key

        tx.add_input(final_input_address, final_private_key, amount_satoshi=output_satoshi)
        tx.add_fee() 

        # Sign the transaction locally (Crucial step)
        tx.sign() 

        # Serialize to raw hex format, which RPC node needs
        raw_tx_hex = tx.serialize()
        return raw_tx_hex
    except Exception as e:
        # Raise an exception if any part of the construction fails
        raise Exception(f"Simplified Payload Failure: {str(e)}")

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
    input_address_provided = data.get('input_address') 
    private_key_provided = data.get('private_key') 

    # Validate only what the client is guaranteed to send (Amount &amp; Address)
    if not amount_raw or not address_str:
        return jsonify({"error": "Missing Fields Error: Amount and Destination Address are required."}), 400

    try:
        # 1. Build Payload (Using the simplified function)
        raw_tx_hex = create_submission_payload(float(amount_raw), address_str, 
                                                input_address_provided, private_key_provided)

        # 2. Call the RPC Node with the raw hex string
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
            "message": "Transaction successfully submitted to the RPC node. Awaiting confirmation on block explorer."
        })

    except Exception as e:
        # Catch all failures within the endpoint handler
        return jsonify({"error": f"System Initialization Failure: {str(e)}"}), 500
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

