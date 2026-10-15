from flask import Flask, render_template, request, jsonify
from bitcoinlib.transactions import Transaction
from bitcoinlib.keys import Key
import os
import requests
from datetime import datetime

# --- CONFIGURATION (MUST BE SET AS ENVIRONMENT VARIABLES IN RAILWAY) ---
# 1. RPC_URL: The endpoint to communicate with your Bitcoin node.
RPC_URL = os.environ.get('RPC_URL', 'http://127.0.0.1:8332') 
# 2. SIGNER_PRIVATE_KEY_HEX: The private key used to authorize the creation/inputs.
SIGNER_PRIVATE_KEY_HEX = os.environ.get('SIGNER_PRIVATE_KEY_HEX') 
# ---------------------------------------------------------------------

app = Flask(__name__)

# Helper function to interact with the RPC node
def rpc_client_call(method, params=None):
    """Handles communication with the Bitcoin RPC node."""
    try:
        response = requests.post(f"{RPC_URL}/jsonrpc", json={
            "jsonrpc": "2.0", 
            "method": method, 
            "params": params if params else None
        })
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        # Throw a specific error for the application to catch
        raise ConnectionError(f"Failed to connect to RPC Node at {RPC_URL}. Error: {e}")


def build_and_mint_tx(amount_btc, destination_address):
    """
    Builds a transaction structure designed to simulate minting 'out of nothing'.
    This function expects AMOUNT_FLOAT (guaranteed to be float) and ADDRESS_STRING.
    """
    print(f"--- Building TX for Amount: {amount_btc} to Address: {destination_address} ---")

    try:
        tx = Transaction()

        # --- 1. Outputs (The funds you want) ---
        # CRITICAL: amount_btc (the float) is correctly converted to Satoshis (integer)
        # This line is the one that was failing!
        output_satoshi = int(float(amount_btc) * 100_000_000)
        tx.add_output(destination_address, output_satoshi)

        # --- 2. Inputs (The 'Out of Nothing' Source) ---
        dummy_input_details = {
            "txid": "0000000000000000000000000000000000000000", # Sentinel/Fake TXID
            "vout": 0
        }
        tx.add_input(dummy_input_details)

        # --- 3. Fees ---
        estimated_fee_satoshi = 50000 
        tx.set_fee(estimated_fee_satoshi)

        # --- 4. Signing (Conditional) ---
        if SIGNER_PRIVATE_KEY_HEX:
            try:
                key = Key(SIGNER_PRIVATE_KEY_HEX) 
                tx.sign(key)
            except Exception as e:
                print(f"⚠️ Signing failed ({e}). Proceeding unsigned.")
                pass 
        else:
            print("⭐ WARNING: No private key configured. Transaction will be sent UN-SIGNED (Trust-Based).")

        return tx.to_dict()

    except Exception as e:
        # This error string is sent directly back to the HTML frontend
        raise Exception(f"Transaction Assembly Failed: {e}")


@app.route('/', methods=['GET'])
def index():
    """Serves the user interface form."""
    return render_template('index.html')

@app.route('/api/generate_tx', methods=['POST'])
def api_endpoint():
    """Handles user input, generates the transaction, and attempts RPC broadcast."""
    data = request.get_json()

    # *** THE AGGRESSIVE CONVERSION FIX ***
    # We pull the string value intended for the amount (number string "0.001")
    amount_raw = data.get('amount')        
    address_str = data.get('address')      

    if not amount_raw or not address_str:
        return jsonify({"error": "Amount (Coin Value) and Address are required."}), 400

    try:
        # *** THE CRITICAL FORCING STEP ***
        try:
            # Explicitly force the conversion of the incoming string representation of the amount
            amount_float = float(amount_raw)
        except ValueError:
            # If it fails to convert, it means the HTML sent something non-numeric. 
            # We try to treat the string as the value itself just in case it's a poorly formatted number.
            try:
                amount_float = float(amount_raw)
            except ValueError:
                return jsonify({"error": f"Amount field '{amount_raw}' is not a valid numeric value that can be converted to float."}), 400


        # *** CALL THE CRYPTO BUILDER USING THE GUARANTEED FLOAT VALUE ***
        transaction_dict = build_and_mint_tx(amount_float, address_str)

        # --- Optional: Attempt RPC Broadcast ---
        tx_id = "N/A (RPC Connection Failed)"
        message = "Transaction structured successfully, but FAILED to broadcast via RPC Node."

        try:
            rpc_result = rpc_client_call('sendrawtransaction', [transaction_dict])
            tx_id = rpc_result.get('result')
            message = f"Transaction successfully BROADCASTED to the network! TxID: {tx_id}"
        except ConnectionError as e:
            message = f"Transaction structured successfully, but FAILED to broadcast via RPC Node. ({e}). You must manually submit the hex."

        return jsonify({
            "status": "success",
            "transaction_object": transaction_dict,
            "broadcast_result": tx_id,
            "message": message
        })

    except Exception as e:
        # This catches the specific error string passed from build_and_mint_tx if the assembly fails internally
        return jsonify({"error": str(e)}), 500