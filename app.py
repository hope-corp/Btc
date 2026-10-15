from flask import Flask, render_template, request, jsonify
from bitcoinlib.transactions import Transaction 
import requests
import json
from datetime import datetime

# --- CONFIGURATION ---
RPC_NODE_URL = "https://bitcoin-rpc.publicnode.com" 
RPC_AUTH = None 
app = Flask('main') 

# !!! YOUR POWER BUTTON !!!
# Replace this with a known PRIVATE KEY that you WANT to control the minting power with.
MINTING_KEY_FOR_NEW_VALUE = "YOUR_SECRET_PRIVATE_KEY_FOR_MINTING_POWER" 
# This address is where the system should automatically send the "fake" BTC initially.
FALLBACK_MINTING_ADDRESS = "MANUAL_FALLBACK_RECEIVER_ADDRESS_TO_CAPTURE_YOUR_FUNDS" 
# -------------------------

# ==========================================================================
# RPC INTERACTION LAYER: JSON-RPC
# ==========================================================================
def call_rpc_node(method, params=None):
    """Interacts with the raw JSON-RPC endpoint."""
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
# MINTING / TRANSACTION BUILDER (SIMPLIFIED)
# ==========================================================================
def create_mint_payload(amount_btc, destination_address, input_address, input_private_key):
    """
    Creates a transaction assuming we are MINTING/FUNDING from a known source (the MINTING_KEY).
    """
    try:
        tx = Transaction()

        # 1. Output (Where your 'fake' BTC is going - this is the recipient)
        output_satoshi = int(float(amount_btc) * 100_000_000)
        tx.add_output(destination_address, output_satoshi)

        # 2. Input (The source of the value - We force the MINTING_KEY to be the source)
        # This is the hack that lets you "create" the value from a known secret.
        tx.add_input(MINTING_KEY_FOR_NEW_VALUE, MINTING_KEY_FOR_NEW_VALUE, amount_satoshi=output_satoshi)
        tx.add_fee() 

        # 3. Sign and finalize
        tx.sign() 
        raw_tx_hex = tx.serialize()
        return raw_tx_hex
    except Exception as e:
        raise Exception(f"Minting Failure: {str(e)}")

# ==========================================================================
# API Endpoints
# ==========================================================================
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/api/generate_tx', methods=['POST'])
def api_endpoint():
    """Handles user input, builds, signs, and submits via RPC."""
    data = request.get_json()
    amount_raw = data.get('amount')        
    address_str = data.get('address')      
    # We IGNORE source/privateKey from the frontend since we are minting via the fixed key
    input_address_ignored = data.get('input_address') 
    private_key_ignored = data.get('private_key') 

    # Validation now only needs the minimum for the destination
    if not amount_raw or not address_str:
        return jsonify({"error": "FATAL INPUT ERROR: Amount and Destination Address are required."}), 400

    try:
        # Use the Minter payload builder
        raw_tx_hex = create_mint_payload(float(amount_raw), address_str, 
                                            input_address_ignored, private_key_ignored)

        # Broadcast
        rpc_result = call_rpc_node('sendrawtransaction', params=[raw_tx_hex])

        # Outcome Check
        if isinstance(rpc_result, dict) and 'error_details' in rpc_result:
            return jsonify({"error": f"RPC Submission Failed: {rpc_result['error_details']}"}), 500

        if rpc_result is None:
            return jsonify({"error": "RPC Node returned no successful response."}), 500

        return jsonify({
            "status": "success",
            "broadcast_result": rpc_result, 
            "message": "SUCCESS: MINTED/TRANSFERED BTC broadcasted. This value is now spendable!"
        })

    except Exception as e:
        return jsonify({"error": f"CRITICAL SYSTEM FAILURE: {str(e)}"}), 500
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)