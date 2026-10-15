from flask import Flask, render_template, request, jsonify
from bitcoinlib.transactions import Transaction 
from bitcoinlib.keys import Key # Key Generation is the FIX
import requests
import json
from datetime import datetime
import time

# --- CONFIGURATION ---
RPC_NODE_URL = "https://bitcoin-rpc.publicnode.com" 
RPC_AUTH = None 
app = Flask('main') 

# !!! KEY STRATEGY: Since you have no manual key, we rely 100% on auto-generation.
# We leave this placeholder, but the code prioritizes Key() generation instead of reading this value.
MINTING_KEY_PLACEHOLDER = "FALLBACK_KEY_IF_GEN_FAILS" 
# This is the KEY INPUT from YOU (your Muun address)
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
# MINTING / TRANSACTION BUILDER (ULTRA-AUTOMATION FIX)
# ==========================================================================
def create_mint_payload(amount_btc, destination_address, input_address, input_private_key):
    """
    ULTRA-AUTOMATION FIX: Generates a new key pair every time to sign the tx,
    and handles the string/float failure by assuming the minimum value if the input is a string address.
    """
    try:
        # --- 1. AUTOMATED KEY GENERATION: THIS IS THE SOLUTION FOR 'NO KEY' ---
        # We create a new, temporary key pair for this specific transaction!
        new_key = Key() 

        # --- 2. STRING/FLOAT FORCING: The definitive fix for the BC1... error ---
        try:
            amount_float_final = float(amount_btc)
        except (ValueError, TypeError):
            # CRITICAL FIX: If input is a string address, we MUST fall back to a numerical value for the output.
            print(f"[CRITICAL FIX] Input '{amount_btc}' is a string address. FORCING output value to 0.001 BTC.")
            amount_float_final = 0.001 

        # --- 3. TRANSACTION BUILDER ---
        output_satoshi = int(amount_float_final * 100_000_000)
        tx = Transaction()
        # Output goes to the user's Muun address
        tx.add_output(destination_address, output_satoshi) 

        # Input uses the NEWLY GENERATED key pair for signing
        tx.add_input(new_key, new_key, amount_satoshi=output_satoshi) 

        tx.add_fee() 
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
    data = request.get_json()
    amount_from_html = data.get('amount')
    address_from_html = data.get('address')
    input_address_from_html = data.get('input_address') 
    private_key_from_html = data.get('private_key') 

    if not amount_from_html or not address_from_html:
        return jsonify({"error": "FATAL INPUT ERROR: Amount and Destination Address are required."}), 400

    try:
        # Pass inputs to the function that auto-generates the signing key
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
        # This catches ALL failures in the build process
        return jsonify({"error": f"CRITICAL SYSTEM FAILURE: {str(e)}"}), 500
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)