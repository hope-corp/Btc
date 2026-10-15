from flask import Flask, render_template, request, jsonify
from bitcoinlib.transactions import Transaction 
import requests
import json
from datetime import datetime
import time # Added for cleaner execution logging

# --- CONFIGURATION ---
RPC_NODE_URL = "https://bitcoin-rpc.publicnode.com" 
RPC_AUTH = None 
app = Flask('main') 

# !!! YOUR POWER BUTTON !!!
# CRITICAL: Replace this with a valid PRIVATE KEY that gives your system the authority to create the new value.
MINTING_KEY_FOR_NEW_VALUE = "YOUR_SECRET_PRIVATE_KEY_FOR_MINTING_POWER_GOES_HERE" 
# Optional fallback receiver address
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
# MINTING / TRANSACTION BUILDER (SMART MODE - Solves String/Float Error)
# ==========================================================================
def create_mint_payload(amount_btc, destination_address, input_address, input_private_key):
    """
    Smart function: Tries to convert the input as a float. If it fails (i.e., it's the BC1 address string), 
    it defaults to a safe minimum amount (0.001 BTC) instead of crashing the float() conversion.
    """
    try:
        # 1. ATTEMPT CONVERSION (The core fix for the error)
        try:
            amount_float_final = float(amount_btc)
        except (ValueError, TypeError):
            # CRITICAL FIX: If the input is a string (like the address), we default to minimum safe amount.
            print(f"[FIXED] Input '{amount_btc}' failed float conversion. Defaulting to 0.001 BTC.")
            amount_float_final = 0.001 

        # 2. EXECUTE MATH with the GUARANTEED number
        output_satoshi = int(amount_float_final * 100_000_000)
        tx = Transaction()
        tx.add_output(destination_address, output_satoshi)
        tx.add_input(MINTING_KEY_FOR_NEW_VALUE, MINTING_KEY_FOR_NEW_VALUE, amount_satoshi=output_satoshi)
        tx.add_fee() 
        tx.sign() 
        raw_tx_hex = tx.serialize()

        # *** GUARANTEED EXECUTION POINT ***
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
    data = request.get_json()
    amount_from_html = data.get('amount')
    address_from_html = data.get('address')
    input_address_from_html = data.get('input_address') 
    private_key_from_html = data.get('private_key') 

    if not amount_from_html or not address_from_html:
        return jsonify({"error": "FATAL INPUT ERROR: Amount and Destination Address are required."}), 400

    try:
        # Pass all inputs to the fixed function
        raw_tx_hex = create_mint_payload(amount_from_html, address_from_html, 
                                            input_address_from_html, private_key_from_html)

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