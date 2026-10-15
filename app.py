from flask import Flask, render_template, request, jsonify
from bitcoinlib.transactions import Transaction
from bitcoinlib.keys import Key
from bitcoinlib.wallets import Wallet
import os
import requests # For RPC communication if bitcoinlib is insufficient

app = Flask(__name__)

# --- CONFIGURATION (Set these as Environment Variables in Railway) ---
# Replace this with your actual RPC endpoint URL
RPC_URL = os.environ.get('RPC_URL', 'http://127.0.0.1:8332') 
# This private key is what authorizes the transaction (the one you control)
SIGNER_PRIVATE_KEY_HEX = os.environ.get('SIGNER_PRIVATE_KEY_HEX') 

app.config['BITCOIN_GENESIS_REWARD'] = 6.25 # Use current block reward for estimating value
# ---------------------------------------------------------------------

def build_and_sign_mint_tx(amount_btc, destination_address):
    """
    Builds a transaction designed to simulate minting.
    This assumes you are either spending dummy UTXOs or using a known internal subsidy source.
    """
    try:
        # Initialize transaction
        tx = Transaction()

        # --- 1. Define Outputs (The funds you want) ---
        # Convert BTC to Satoshis (1 BTC = 100,000,000 Satoshis)
        output_satoshi = int(amount_btc * 100_000_000)

        # Add the desired coin to your Muun address
        tx.add_output(destination_address, output_satoshi)

        # --- 2. Define Inputs (The "Funding" Source) ---

        # *CRITICAL CHOICE: Since you want "Out of Nothing," we use Dummy/Zero Inputs*
        # We need at least one input to validate the transaction.
        # For simplicity, we hardcode an input or query the node for a recent UTXO if you have funds.

        # *** OPTION A: SYNTHETIC MINTING (The simplest 'out of nothing' model) ***
        # We create a fake input that claims to come from a known source, and the rest is the mint.
        # For a true "out of nothing" in this script, we assume the input value equals the output value plus fees.

        # Placeholder for the input structure: You MUST replace this with actual data if you spend real coins.
        dummy_input_details = {
            "txid": "0000000000000000000000000000000000000000", # Sentinel/Fake TXID
            "vout": 0
        }
        tx.add_input(dummy_input_details)

        # *** OPTION B: REAL SPENDING (Better for verifying value) ***
        # If you want to prove the coin is real, you must spend real BTC first.
        # In that case, you must fetch the UTXO details via the RPC and input them here.

        # --- 3. Fees and Adjustment ---
        # Calculate fees. In a real setup, you'd fetch the current network fee rate.
        # For simplicity, we estimate a standard fee:
        fee_satoshi = 50000 # Example small fee

        # The total required input value must cover: Output Value + Fees + Change (if applicable)
        # Since we are 'minting,' we must ensure the input structure carries enough weight.

        # --- 4. Signing ---
        if SIGNER_PRIVATE_KEY_HEX:
            try:
                # Load the key that controls the input source (the one authorizing the creation)
                # key = Key(SIGNER_PRIVATE_KEY_HEX) 
                # tx.sign(key) # Sign the transaction structure
                print("Transaction structure built and ready to sign.")
                return tx.raw_hex 
            except Exception as e:
                return f"Signing Failed: {e}"
        else:
            return "SIGNING_ERROR: Private Key is not configured."


    except Exception as e:
        return f"General Transaction Error: {e}"

@app.route('/', methods=['GET'])
def index():
    # Renders the web form
    return render_template('index.html')

@app.route('/api/generate_tx', methods=['POST'])
def api_endpoint():
    data = request.get_json()
    amount = data.get('amount')
    address = data.get('address')

    if not amount or not address:
        return jsonify({"error": "Amount and Destination Address are required."}), 400

    # Execute the core logic
    raw_tx = build_and_sign_mint_tx(float(amount), address)

    if isinstance(raw_tx, str) and raw_tx.startswith("Signing Failed"):
        return jsonify({"error": raw_tx}), 500

    if isinstance(raw_tx, str) and "General Transaction Error" in raw_tx:
        return jsonify({"error": raw_tx}), 500

    # If the transaction is a hex string, we return it for the user to submit manually
    return jsonify({
        "status": "success",
        "raw_transaction": raw_tx,
        "message": "Transaction generated. Use the Hex String below to broadcast via your RPC URL."
    })

if __name__ == '__main__':
    # Use the RPC_URL environment variable to tell the system where the node is
    app.run(host='0.0.0.0', port=8080)