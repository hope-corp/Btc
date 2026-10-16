# --- Imports ---
from flask import Flask, render_template, request
from bitcoinlib import transactions 
from bitcoinlib.keys import Key 
from decimal import Decimal, getcontext
import os
import requests 
# Note: If you need advanced crypto functions (like the ones we discussed), 
# you would import ecdsa and base58 here.

# --- 1. Initialization ---
app = Flask(__name__)

# Set precision high for financial calculations to handle BTC fractions accurately
getcontext().prec = 28

# Configuration
CHANGE_ADDRESS_PLACEHOLDER = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa" 
BTC_TO_SAT = 100_000_000
# Target RPC Node for external validation
RPC_NODE_URL = "https://bitcoin-rpc.publicnode.com" 

# --- 2. Functions ---

def submit_transaction_to_rpc(tx_hex):
    """
    Submits the signed raw transaction hex to the public Bitcoin RPC Node using JSON-RPC format.
    """
    try:
        # RPC nodes often require a specific JSON structure for the method call
        headers = {'Content-Type': 'application/json'}
        payload = {
            "jsonrpc": "1.0",
            "id": "flask-bitcoin-tool",
            "method": "sendrawtransaction",
            "params": [tx_hex]
        }

        response = requests.post(RPC_NODE_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status() # Raises HTTPError for 4xx/5xx responses
        data = response.json()

        if "error" in data and data["error"]:
            # This catches the specific UTXO/Validation errors you encountered
            return f"Node Rejected: {data['error'].get('message', 'Unknown RPC validation error')}"

        # 'result' in successful submissions is the transaction hash
        return f"Success! TXID: {data.get('result')}"

    except requests.exceptions.HTTPError as http_err:
        # Specifically handles the 400 Bad Request error from the node
        return f"HTTP Error {http_err.response.status_code}: {http_err.response.text}"
    except requests.exceptions.RequestException as req_err:
        return f"RPC Connection Error: Could not reach or communicate with the node. {req_err}"
    except Exception as e:
        return f"RPC Processing Error: {str(e)}"


def generate_fake_transaction(amount_btc_decimal, dest_address, private_key_hex):
    """
    Generates, signs, and prepares a transaction.
    This function is the core logic that simulates the transaction structure.
    """
    try:
        amount_satoshi = int(amount_btc_decimal * BTC_TO_SAT)
        simulated_fee_satoshi = int(Decimal('0.001') * BTC_TO_SAT) 
        total_input_satoshi = amount_satoshi + simulated_fee_satoshi

        tx = transactions.Transaction()
        # Output 1: The actual recipient
        tx.add_output(amount_satoshi, address=dest_address) 
        # Output 2: The change back to the sender
        tx.add_output(simulated_fee_satoshi, address=CHANGE_ADDRESS_PLACEHOLDER)

        # --- CRITICAL MOCK UTXO ---
        # This is the required input that the node must validate against the blockchain.
        mock_input_txid = "1111111111111111111111111111111111111111111111111111111111111111" 
        mock_input_vout = 0

        # Load the key provided by the user
        sender_key = Key(private_key_hex)

        # Add simulated input, tying the input value to the required total spending
        tx.add_input(
            prev_txid=mock_input_txid, 
            output_n=mock_input_vout, 
            keys=sender_key,
            value=total_input_satoshi # CRITICAL: This must match the total of outputs
        )
        tx.sign() # Performs the ECDSA signing based on the input details

        confirmation_status = "Prepared (Awaiting RPC Submission)"
        transaction_hex = tx.as_hex()

        total_btc_transferred = Decimal(total_input_satoshi) / BTC_TO_SAT

        return {
            "status": confirmation_status, 
            "tx_hex": transaction_hex,
            "total_btc_transferred": total_btc_transferred,
            "original_amount_sent": amount_btc_decimal
        }
    except Exception as e:
        return f"Final Validation Error: {str(e)} (Transaction library failure)."

# --- 3. Routes ---
@app.route('/', methods=['GET'])
def index():
    # Requires templates/index.html to be in place
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

        # --- Automatic Key Generation for First-Time Users ---
        if not private_key_hex:
            # Generate a fresh keypair if the user leaves the field blank
            temp_key = Key()
            # We use WIF form as it's standard, but the system can use raw keys too
            private_key_hex = temp_key.wif() 
            print(f"--> Auto-Generated Key: {private_key_hex} | Suggested Address: {temp_key.address}")

        # Step 1: Generate the transaction object and signature
        data = generate_fake_transaction(amount_btc_decimal, dest_address, private_key_hex)

        if isinstance(data, str):
             return render_template('index.html', result=f"Transaction Library Error: {data}")

        tx_hex = data['tx_hex']

        # Step 2: Submit the transaction to the RPC Node for real-world validation
        rpc_status_message = submit_transaction_to_rpc(tx_hex)

        # --- Final Response Assembly ---
        return render_template(
            'index.html', 
            result=f"GENERATION SUCCESS: {data['status']} | Submission Status: {rpc_status_message}", 
            transaction_data=tx_hex, 
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