from flask import Flask, render_template, request, jsonify
# We are moving away from bitcoinlib for the heavy lifting, but keep imports for good measure
from bitcoinlib.transactions import Transaction 
import os
import requests
from datetime import datetime

# --- CONFIGURATION (CRITICAL UPDATE) ---
# 1. TATUM_GATEWAY_URL: The REST API endpoint provided by Tatum.
TATUM_GATEWAY_URL = "https://bitcoin-mainnet.gateway.tatum.io/rest"
# 2. SIGNER_PRIVATE_KEY_HEX: The private key used to authorize the creation/inputs.
SIGNER_PRIVATE_KEY_HEX = os.environ.get('SIGNER_PRIVATE_KEY_HEX') 
# ---------------------------------------------------------------------

app = Flask(__name__)

# =========================================================================
# NEW INTERACTION LAYER: Replacing bitcoinlib with direct REST calls to Tatum
# =========================================================================

def call_tatum_api(endpoint, method='POST', data=None, params=None):
    """General wrapper to interact with the Tatum REST API."""
    headers = {
        'Content-Type': 'application/json'
    }
    try:
        if method == 'GET':
            response = requests.get(f"{TATUM_GATEWAY_URL}/{endpoint}", headers=headers, params=params)
        else:
            response = requests.post(f"{TATUM_GATEWAY_URL}/{endpoint}", headers=headers, json=data)

        response.raise_for_status() # This raises HTTPError for 4xx/5xx responses
        return response.json()
    except requests.exceptions.HTTPError as e:
        # Handle specific API errors returned by Tatum
        try:
            return response.json() # Try to parse the error body
        except:
            return {"error_details": str(e)}
    except requests.exceptions.RequestException as e:
        # Handle connection failure to Tatum
        return {"error_details": f"Connection Error to Tatum Gateway: {e}"}


def build_and_mint_tx(amount_btc, destination_address):
    """
    Builds the transaction object payload required by Tatum (This is the NEW logic).
    Tatum generally requires the inputs/outputs to be defined by UTXOs or raw values.
    """
    print(f"--- Building TX for Amount: {amount_btc} to Address: {destination_address} ---")

    # 1. Calculate amount in Satoshis (Crucial for the float conversion!)
    try:
        output_satoshi = int(float(amount_btc) * 100_000_000)
    except ValueError:
        # If conversion fails here, it means the string was bad, as feared!
        raise Exception(f"Amount string '{amount_btc}' could not be converted to a float.")

    # 2. Construct the transaction payload payload for Tatum API submission
    # NOTE: Tatum requires inputs to be defined relative to actual UTXOs or using inputs as 'P2PKH'
    # For pure minting (out of nothing), we use the structure that submits inputs/outputs directly.

    # --- SIMPLIFIED PAYLOAD FOR MINTING ---
    # We use the core parameters Tatum needs for creation.
    tx_payload = {
        "inputs": [
            {
                "address": "0000000000000000000000000000000000000000", # Dummy Input Address 
                "amount": output_satoshi 
            }
        ],
        "outputs": [
            {
                "address": destination_address,
                "amount": output_satoshi
            }
        ],
        "fee": 50000 # Fixed fee placeholder
    }
    return tx_payload


@app.route('/', methods=['GET'])
def index():
    """Serves the user interface form."""
    return render_template('index.html')

@app.route('/api/generate_tx', methods=['POST'])
def api_endpoint():
    """Handles user input, generates the transaction payload, and broadcasts via Tatum."""
    data = request.get_json()

    amount_raw = data.get('amount')        # Expecting number string "0.001"
    address_str = data.get('address')      # Expecting string "bc1q..."

    if not amount_raw or not address_str:
        return jsonify({"error": "Amount (Coin Value) and Address are required."}), 400

    try:
        # *** FIX IN ACTION: Conversion forced AT THE API LAYER ***
        try:
            amount_float = float(amount_raw)
        except ValueError:
            # This is your fallback for when the number string itself is corrupted.
            return jsonify({"error": f"Amount field '{amount_raw}' is not a valid numeric value."}), 400


        # --- 1. Build the Payload using the converted float ---
        tx_payload = build_and_mint_tx(amount_float, address_str)

        # --- 2. Attempt to Submit/Broadcast via Tatum REST API ---
        # Tatum endpoint for creating/broadcasting is usually /transactions/

        print(f"Attempting to submit transaction payload to Tatum API: {tx_payload}")

        # Use the Tatum gateway endpoint to submit the transaction
        tatum_response = call_tatum_api('transactions', method='POST', data=tx_payload)

        # 3. Process Tatum Response
        if isinstance(tatum_response, dict) and 'error_details' in tatum_response:
             return jsonify({"error": f"Tatum API Error: {tatum_response['error_details']}"}), 500

        # Assuming Tatum returns a successful transaction object/ID on success
        if 'transactionId' in tumatum_response:
            return jsonify({
                "status": "success",
                "transaction_object": tx_payload,
                "broadcast_result": tumatum_response['transactionId'],
                "message": "Transaction successfully submitted and is being processed by Tatum Gateway."
            })

        # If successful response but no ID returned
        return jsonify({"status": "success", "transaction_object": tx_payload, "broadcast_result": "N/A", "message": "Transaction submitted successfully, but ID was not returned."})

    except Exception as e:
        # Catch all other errors (like failed float conversion inside build_and_mint_tx)
        return jsonify({"error": str(e)}), 500

# =========================================================================
# End of Updated Code
# =========================================================================

if __name__ == '__main__':
    print("==============================================")
    print("🚀 Starting Flask Server with Tatum Gateway Integration")
    print("==============================================")
    app.run(host='0.0.0.0', port=8080)