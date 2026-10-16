from flask import Flask, render_template, request
from bitcoinlib import transactions, keys 
import json
from decimal import Decimal, getcontext
import os
import requests # <--- NEW IMPORT
from datetime import datetime # <-- NEW IMPORT

# --- 1. Initialization ---
app = Flask(__name__)

# Set precision high for financial calculations to handle BTC fractions accurately
getcontext().prec = 28

# Configuration
# NOTE: Using a real exchange address for better simulation fidelity if possible
CHANGE_ADDRESS_PLACEHOLDER = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa" 
BTC_TO_SAT = 100_000_000
RPC_NODE_URL = "https://bitcoin-rpc.publicnode.com" # Target RPC Node

# --- 2. Functions ---
def generate_transaction_data(amount_btc_decimal, dest_address, private_key_hex):
    """
    Generates and signs the raw transaction hex string.
    Returns a dictionary containing validation status AND the hex string.
    """
    try:
        amount_satoshi = int(amount_btc_decimal * BTC_TO_SAT)
        simulated_fee_satoshi = int(Decimal('0.001') * BTC_TO_SAT) 

        tx = transactions.Transaction()
        tx.add_output(amount_satoshi, address=dest_address) 
        tx.add_output(simulated_fee_satoshi, address=CHANGE_ADDRESS_PLACEHOLDER)

        mock_input_txid = "0000000000000000000000000000000000000000000000000000000000000000" 
        mock_input_vout = 0

        if private_key_hex:
            sender_key = Key(private_key_hex, is_wif=False)
            tx.add_input(prev_txid=mock_input_txid, output_n=mock_input_vout, keys=sender_key)
            tx.sign()
        else:
            tx.add_input(prev_txid=mock_input_txid, output_n=mock_input_vout)

        confirmation_status = "Prepared (Awaiting RPC Submission)"
        transaction_hex = tx.as_hex()

        total_btc_transferred = tx.output_total / BTC_TO_SAT

        # Return structured data for the route to process
        return {
            "status": confirmation_status, 
            "tx_hex": transaction_hex,
            "total_btc_transferred": total_btc_transferred,
            "original_amount_sent": amount_btc_decimal
        }
    except Exception as e:
        return f"Final Validation Error: {str(e)} (Transaction library failure)."


def submit_transaction_to_rpc(tx_hex):
    """
    Submits the raw transaction hex to the public node and returns the RPC response.
    """
    print(f"\n--- Attempting RPC Submission to {RPC_NODE_URL} ---")
    try:
        # The RPC endpoint expects a POST request with the transaction hex
        rpc_response = requests.post(
            RPC_NODE_URL, 
            data=tx_hex, 
            headers={'Content-Type': 'application/hex'}
        )
        rpc_response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)

        # Assuming the response is JSON containing the confirmation status
        rpc_data = rpc_response.json()

        # Check the RPC response structure for success/status
        if rpc_data.get('result') and rpc_data['result'] == 'true':
             return "✅ SUCCESS! Transaction submitted to RPC Node and confirmed by node status."
        else:
             return f"⚠️ WARNING: RPC Node accepted the submission, but the result was not 'true'. Details: {rpc_data.get('message', 'No message provided.')}"

    except requests.exceptions.RequestException as e:
        return f"❌ RPC CONNECTION FAILED: Could not reach or communicate with the node. Error: {e}"
    except json.JSONDecodeError:
        return f"❌ RPC PARSING FAILED: Node responded, but the response was not valid JSON. Raw response: {rpc_response.text[:100]}..."


# --- 3. Routes ---
@app.route('/', methods=['GET'])
def index():
    # Assuming you have index.html in a 'templates' folder
    return render_template('index.html')

@app.route('/send', methods=['POST'])
def send_transaction():
    try:
        amount_str = request.form.get('amount')
        dest_address = request.form.get('destination')
        private_key_hex = request.form.get('sender_private_key', '').strip() 

        if not amount_str or not dest_address:
            return render_template('index.html', result="Error: Amount and Destination address are required.")

        amount_btc_decimal = Decimal(amount_str)

        # Step 1: Generate the transaction data
        data = generate_transaction_data(amount_btc_decimal, dest_address, private_key_hex)

        # Check for library errors during generation
        if isinstance(data, str):
             return render_template('index.html', result=f"Transaction Library Error: {data}")

        tx_hex = data['tx_hex']

        # Step 2: Submit the transaction to the RPC Node
        rpc_status_message = submit_transaction_to_rpc(tx_hex)

        # --- Final Response Assembly ---
        return render_template(
            'index.html', 
            result=f"GENERATION SUCCESS: {data['status']} | Submission Status: {rpc_status_message}", 
            transaction_data=tx_hex, # Report the hex string itself
            total_btc_transferred=data['total_btc_transferred']
        )

    except ValueError:
        return render_template('index.html', result="Error: Invalid amount format provided.")
    except Exception as e:
        return render_template('index.html', result=f"System Error: {str(e)}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    is_debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=is_debug)