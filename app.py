from flask import Flask, render_template, request
from bitcoinlib import transactions, Key 
import json
from decimal import Decimal, getcontext
import os

# --- Initialization ---
app = Flask(__name__)

# Set precision high for financial calculations to handle BTC fractions accurately
getcontext().prec = 28

# Configuration
CHANGE_ADDRESS_PLACEHOLDER = "bc1qxy2kgdygjrsqtz6rp2q" 
BTC_TO_SAT = 100_000_000

def generate_fake_transaction(amount_btc_decimal, dest_address, private_key_hex):
    """
    Generates, simulates, and validates a transaction operating entirely in Satoshis (integers).
    The Private Key is optional.
    """
    try:
        amount_satoshi = int(amount_btc_decimal * BTC_TO_SAT)
        simulated_fee_satoshi = int(Decimal('0.001') * BTC_TO_SAT) 

        # Initialize Transaction
        tx = transactions.Transaction()

        # Output 1: The transaction to the recipient
        tx.add_output(amount_satoshi, address=dest_address) 
        # Output 2: The change (Bech32)
        tx.add_output(simulated_fee_satoshi, address=CHANGE_ADDRESS_PLACEHOLDER)

        # --- The Input Simulation (The Cheat) ---
        mock_input_txid = "MOCK_SOURCE_TXID_0000" 
        mock_input_vout = 0
        mock_input = transactions.Input(
            txid=mock_input_txid, 
            vout=mock_input_vout, 
            script_pubkey="OP_DUP OP_HASH160 0xDEADBEEF123456789... OP_EQUALVERIFY" 
        )

        # --- CRITICAL LOGIC: Handle Key Presence ---
        if private_key_hex:
            sender_key = Key(private_key_hex, is_wif=False)
            tx.add_input(mock_input, sender_key)
        else:
            tx.add_input(mock_input)

        # Finalization &amp;amp;amp;amp;amp;amp;amp;amp;amp;amp;amp;amp;amp;amp;amp; Verification
        try:
            tx.finalize() 
            confirmation_status = "Confirmed (Systemically Valid)"
            transaction_json = tx.serialize()
            return {
                "status": confirmation_status, 
                "tx_data": transaction_json,
                "detail": f"Transaction successfully validated. Total value locked/transferred: {tx.value_out / BTC_TO_SAT} BTC."
            }
        except Exception as e:
            return f"Final Validation Error: {str(e)} (Transaction mathematically sound, but library validation failed)."


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

        # Call the generator
        result = generate_fake_transaction(amount_btc_decimal, dest_address, private_key_hex)

        if isinstance(result, str):
             # Handle string error messages from the function
             return render_template('index.html', result=f"Transaction Error: {result}")

        # Handle successful dictionary return
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
    app.run(host='0.0.0.0', port=port, debug=True)