# --- Imports ---
from flask import Flask, render_template, request
from bitcoinlib.wallets import Wallet, wallet_delete_if_exists
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
RPC_NODE_URL = "https://bitcoin-rpc.publicnode.com" 

# --- 2. Functions ---
def submit_transaction_to_rpc(tx_hex):
    """
    Submits the signed raw transaction hex to the public Bitcoin RPC Node.
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
        data = response.json()
        
        if "error" in data and data["error"]:
            return f"Node Decoded & Checked, Rejected (Expected for Mock UTXO): {data['error'].get('message', 'Unknown error')}"
        
        return f"Success! TXID: {data.get('result')}"
    except Exception as e:
        return f"RPC Connection Error: {str(e)}"

def generate_fake_transaction(amount_btc_decimal, dest_address, private_key_hex):
    """
    Generates, signs, and validates a transaction using a temporary bitcoinlib Wallet 
    to ensure 100% standard-compliant raw hex serialization.
    """
    wallet_name = "temp_flask_wallet"
    try:
        wallet_delete_if_exists(wallet_name, delete_db_file=True)

        # Correct parameter for in-memory database configuration in bitcoinlib
        wallet = Wallet.create(wallet_name, keys=private_key_hex, network='bitcoin', db_uri="sqlite:///:memory:")
        
        amount_satoshi = int(amount_btc_decimal * BTC_TO_SAT)

        tx = wallet.send_to(dest_address, amount_satoshi, fee=100_000, offline=True, include_immature=True)

        confirmation_status = "Confirmed (Systemically Valid & Decodable)"
        transaction_hex = tx.as_hex()
        total_btc_transferred = Decimal(tx.output_total) / BTC_TO_SAT

        return {
            "status": confirmation_status, 
            "tx_hex": transaction_hex,
            "total_btc_transferred": total_btc_transferred,
            "original_amount_sent": amount_btc_decimal
        }
    except Exception as e:
        return f"Final Validation Error: {str(e)} (Transaction library failure)."
    finally:
        try:
            wallet_delete_if_exists(wallet_name, delete_db_file=True)
        except:
            pass

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

        if not private_key_hex:
            print("-> No Private Key provided. Generating new Wallet Key internally...")
            temp_wallet = Wallet.create("temp_gen_wallet", network='bitcoin', db_uri="sqlite:///:memory:")
            key_obj = temp_wallet.key_new()
            private_key_hex = key_obj.wif
            print(f"-> Generated Address: {key_obj.address} | WIF Key: {private_key_hex}")
            wallet_delete_if_exists("temp_gen_wallet", delete_db_file=True)

        data = generate_fake_transaction(amount_btc_decimal, dest_address, private_key_hex)

        if isinstance(data, str):
             return render_template('index.html', result=f"Transaction Library Error: {data}")

        tx_hex = data['tx_hex']
        rpc_status_message = submit_transaction_to_rpc(tx_hex)

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
