# app.py
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
    The logic is corrected to ensure amount_btc is correctly used for float conversion.
    """
    print(f"--- Building TX for Amount: {amount_btc} to Address: {destination_address} ---")

    try:
        tx = Transaction()

        # --- 1. Outputs (The funds you want) ---
        # CRITICAL: amount_btc (the float) is correctly converted to Satoshis (integer)
        output_satoshi = int(float(amount_btc) * 100_000_000)
        tx.add_output(destination_address, output_satoshi)

        # --- 2. Inputs (The 'Out of Nothing' Source) ---
        # Placeholder Input for Pure Minting (We assume this is the subsidy source)
        dummy_input_details = {
            "txid": "0000000000000000000000000000000000000000", # Sentinel/Fake TXID
            "vout": 0
        }
        tx.add_input(dummy_input_details)

        # --- 3. Fees ---
        # You MUST estimate fees based on the live network rate if you want real value.
        # Using a fixed small fee for this pure minting model:
        estimated_fee_satoshi = 50000 
        tx.set_fee(estimated_fee_satoshi)

        # --- 4. Signing (Conditional) ---
        if SIGNER_PRIVATE_KEY_HEX:
            try:
                # If a key is provided, we attempt to sign (stronger validation)
                key = Key(SIGNER_PRIVATE_KEY_HEX) 
                tx.sign(key)
                print("✅ Transaction structure built and signed successfully.")
            except Exception as e:
                # If signing fails, we proceed unsigned but alert the user
                print(f"⚠️ Signing failed ({e}). Proceeding unsigned.")
                # If signing fails, we must manually verify the transaction state if possible
                pass 
        else:
            print("⭐ WARNING: No private key configured. Transaction will be sent UN-SIGNED (Trust-Based).")

        # Return the dictionary structure for easier consumption by the HTML frontend
        return tx.to_dict()

    except Exception as e:
        # Re-raise the specific error type for the API endpoint to catch it
        raise Exception(f"Transaction Assembly Failed: {e}")


@app.route('/', methods=['GET'])
def index():
    """Serves the user interface form."""
    return render_template('index.html')

@app.route('/api/generate_tx', methods=['POST'])
def api_endpoint():
    """Handles user input, generates the transaction, and attempts RPC broadcast."""
    data = request.get_json()

    # *** CRITICAL FIX AREA ***
    # We are pulling the value intended for AMOUNT and the string intended for ADDRESS.
    amount_str = data.get('amount')
    address_str = data.get('address')

    if not amount_str or not address_str:
        return jsonify({"error": "Amount (Coin Value) and Address are required."}), 400

    try:
        # The call uses the CORRECT order: (Coin Value, Address String)
        transaction_dict = build_and_mint_tx(amount_str, address_str)

        # --- Optional: Attempt RPC Broadcast ---
        tx_id = "N/A (RPC Connection Failed)"
        message = "Transaction structured successfully, but FAILED to broadcast via RPC Node."

        try:
            # We pass the dictionary representation of the transaction
            rpc_result = rpc_client_call('sendrawtransaction', [transaction_dict])
            tx_id = rpc_result.get('result')
            message = f"Transaction successfully BROADCASTED to the network! TxID: {tx_id}"
        except ConnectionError as e:
            # This is the expected fallback if RPC is down
            message = f"Transaction structured successfully, but FAILED to broadcast via RPC Node. ({e}). You must manually submit the hex."


        return jsonify({
            "status": "success",
            "transaction_object": transaction_dict,
            "broadcast_result": tx_id,
            "message": message
        })

    except Exception as e:
        # Catches the specific "Transaction Assembly Failed" error raised in build_and_mint_tx
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("==============================================")
    print("🚀 Starting Flask Server for BTC Mint Generator")
    print("==============================================")
    app.run(host='0.0.0.0', port=8080)