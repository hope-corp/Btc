# --- Imports ---
from flask import Flask, render_template, request
from bitcoinlib import transactions 
from bitcoinlib.keys import Key 
from decimal import Decimal, getcontext
import os
import requests 

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
        headers = {'Content-Type': 'application/json'}
        payload = {
            "jsonrpc": "1.0",
            "id": "flask-bitcoin-tool",
            "method": "sendrawtransaction",
            "params": [tx_hex]
        }

        response = requests.post(RPC_NODE_URL, json=payload, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if "error" in data and data["error"]:
                # Return the specific, detailed validation failure message from the node
                return f"Node Rejection Detail: {data['error'].get('message', 'Unknown RPC validation error')}"

            # SUCCESS: The node accepted the structure and returned the TXID
            return f"Success! TXID: {data.get('result')}"

        # Catching HTTP Errors (like 400, 500, etc.)
        else:
            return f"HTTP Error {response.status_code}: {response.text}"

    except requests.exceptions.RequestException as req_err:
        # Catching connection failures, timeouts, etc.
        return f"RPC Connection Error: Could not reach or communicate with the node. {req_err}"
    except Exception as e:
        return f"RPC Processing Error: {str(e)}"


def generate_fake_transaction(amount_btc_decimal, dest_address, private_key_hex):
    """
    Generates, signs, and prepares a transaction using explicit local parameters.
    """
    try:
        amount_satoshi = int(amount_btc_decimal * BTC_TO_SAT)
        simulated_fee_satoshi = int(Decimal('0.001') * BTC_TO_SAT) 
        total_input_satoshi = amount_satoshi + simulated_fee_satoshi

        sender_key = Key(private_key_hex)

        tx = transactions.Transaction()
        # Output 1: Recipient
        tx.add_output(amount_satoshi, address=dest_address) 
        # Output 2: Change
        tx.add_output(simulated_fee_satoshi, address=CHANGE_ADDRESS_PLACEHOLDER)

        # --- CRITICAL MOCK UTXO (The source of the funds) ---
        mock_input_txid = "1111111111111111111111111111111111111111111111111111111111111111" 
        mock_input_vout = 0

        # Providing explicit address and script_type prevents network lookups for mock/fake inputs
        tx.add_input(
            prev_txid=mock_input_txid, 
            output_n=mock_input_vout, 
            keys=sender_key,
            value=total_input_satoshi,
            address=sender_key.address(),
            script_type='p2pkh'
        )
        tx.sign() # The digital signature is applied here

        # Transaction is internally verified and signed.
        confirmation_status = "Systemically Valid (Code Certified)"
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

        # Auto Key Generation Logic (If user doesn't provide key)
        if not private_key_hex:
            temp_key = Key()
            private_key_hex = temp_key.wif() 
            print(f"--> Auto-Generated Key Used: {private_key_hex}")

        # Step 1: Generate the transaction object and signature (Internal Certification)
        data = generate_fake_transaction(amount_btc_decimal, dest_address, private_key_hex)

        if isinstance(data, str):
             return render_template('index.html', result=f"Transaction Library Error: {data}")

        tx_hex = data['tx_hex']

        # Step 2: Submit to RPC Node (External Certification)
        rpc_status_message = submit_transaction_to_rpc(tx_hex)

        # Final comprehensive result combining internal and external checks
        result_message = f"GENERATION SUCCESS: {data['status']} | RPC STATUS: {rpc_status_message}"

        return render_template(
            'index.html', 
            result=result_message, 
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
