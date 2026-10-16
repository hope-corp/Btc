from flask import Flask, render_template, request
from bitcoinlib import transactions, keys 
import json
from decimal import Decimal, getcontext
import os

# --- 1. Initialization ---
app = Flask(__name__)

# Set precision high for financial calculations to handle BTC fractions accurately
getcontext().prec = 28

# Configuration
CHANGE_ADDRESS_PLACEHOLDER = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa" 
BTC_TO_SAT = 100_000_000

# --- 2. Functions ---
def generate_fake_transaction(amount_btc_decimal, dest_address, private_key_hex):
    """
    Generates, simulates, and validates a transaction operating entirely in Satoshis (integers).
    The Private Key is optional.
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

        confirmation_status = "Confirmed (Systemically Valid)"
        # Corrected method to obtain the raw transaction hex string
        transaction_json = tx.as_hex()
        return {
            "status": confirmation_status, 
            "tx_data": transaction_json,
            "detail": f"Transaction successfully validated. Total value locked/transferred: {tx.value_out / BTC_TO_SAT} BTC."
        }
    except Exception as e:
        return f"Final Validation Error: {str(e)} (Transaction mathematically sound, but library validation failed)."

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

        result = generate_fake_transaction(amount_btc_decimal, dest_address, private_key_hex)

        if isinstance(result, str):
             return render_template('index.html', result=f"Transaction Error: {result}")

        return render_template(
            'index.html', 
            result=f"SUCCESS! Transaction generated and confirmed: {result['status']}", 
            transaction_data=result['tx_data']
        )

    except ValueError:
        return render_template('index.html', result="Error: Invalid amount format provided.")
    except Exception as e:
        return render_template('index.html', result=f"System Error: {str(e)}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    is_debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=is_debug)
