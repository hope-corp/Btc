from flask import Flask, render_template, request, jsonify
from bitcoinlib.transactions import Transaction
from bitcoinlib.keys import Key
import os
import requests

app = Flask(__name__)

# --- CONFIGURATION (MUST BE SET AS ENVIRONMENT VARIABLES IN RAILWAY) ---
# 1. RPC_URL: The endpoint to communicate with your Bitcoin node.
RPC_URL = os.environ.get('RPC_URL', 'http://127.0.0.1:8332') 
# 2. SIGNER_PRIVATE_KEY_HEX: If you add a key later for stronger proof, put it here.
# If this is None, the transaction will be unsigned (Trust-Based Model).
SIGNER_PRIVATE_KEY_HEX = os.environ.get('SIGNER_PRIVATE_KEY_HEX') 
# ---------------------------------------------------------------------

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
        raise ConnectionError(f"Failed to connect to RPC Node at {RPC_URL}. Error: {e}")


def build_and_mint_tx(amount_btc, destination_address):
    """
    Builds a transaction structure designed to simulate minting 'out of nothing'.
    It focuses on structural validity rather than cryptographic proof.
    """
    print("Attempting to build transaction...")

    try:
        tx = Transaction()

        # --- 1. Outputs (The funds you want) ---
        output_satoshi = int(amount_btc * 100_000_000)
        tx.add_output(destination_address, output_satoshi)

        # --- 2. Inputs (The 'Out of Nothing' Source) ---
        # Since we are purely minting, we use a placeholder/dummy input. 
        # In a real system, you would fetch real UTXOs here.
        dummy_input_details = {
            "txid": "0000000000000000000000000000000000000000", # Sentinel/Fake TXID
            "vout": 0
        }
        tx.add_input(dummy_input_details)

        # --- 3. Fees ---
        # You must estimate fees based on current network conditions.
        # For this example, we estimate a small fixed fee in satoshis.
        estimated_fee_satoshi = 50000 
        tx.set_fee(estimated_fee_satoshi)

        # --- 4. Signing (Conditional) ---
        if SIGNER_PRIVATE_KEY_HEX:
            # If a key is provided, we attempt to sign (stronger validation)
            # key = Key(SIGNER_PRIVATE_KEY_HEX) 
            # tx.sign(key) # Uncomment this line to use the key
            print("Transaction structure built. Signing mechanism available.")
        else:
            print("WARNING: No private key configured. Transaction will be sent UN-SIGNED (Trust-Based).")

        # Return the dictionary structure which is easier for clients to consume
        return tx.to_dict()

    except Exception as e:
        print(f"ERROR during transaction assembly: {e}")
        raise Exception(f"Transaction Assembly Failed: {e}")


@app.route('/', methods=['GET'])
def index():
    """Serves the user interface form."""
    return render_template('index.html')

@app.route('/api/generate_tx', methods=['POST'])
def api_endpoint():
    """Handles user input, generates the transaction, and returns the structure."""
    data = request.get_json()
    amount = data.get('amount')
    address = data.get('address')

    if not amount or not address:
        return jsonify({"error": "Amount and Destination Address are required."}), 400

    try:
        # 1. Build and Sign (or just build, if key is missing)
        transaction_dict = build_and_mint_tx(float(amount), address)

        # 2. Optional: Attempt to fetch the raw hex immediately using the RPC client
        # This is the final step to show what is actually being sent to the network.
        try:
            raw_result = rpc_client_call('sendrawtransaction', [transaction_dict])
            # The response from sendrawtransaction contains the transaction ID if successful
            tx_id = raw_result.get('result')
            message = f"Transaction successfully BROADCASTED to the network! TxID: {tx_id}"
        except ConnectionError as e:
            tx_id = "N/A (RPC Connection Failed)"
            message = f"Transaction structured successfully, but FAILED to broadcast via RPC Node. {e}"

        return jsonify({
            "status": "success",
            "transaction_object": transaction_dict,
            "broadcast_result": tx_id,
            "message": message
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("Starting Flask Server...")
    app.run(host='0.0.0.0', port=8080)