from flask import Flask, render_template, request
# --- FIX APPLIED: Using transactions.* based on error logs ---
from bitcoinlib import transactions, keys 
import json
from decimal import Decimal, getcontext
import os

app = Flask(__name__)

# Set precision high for financial calculations to handle BTC fractions accurately
getcontext().prec = 28

# --- Configuration ---
# This address is used internally as the recipient of the change (the "fees")
CHANGE_ADDRESS_PLACEHOLDER = "ChangeAddressPlaceholder"

def generate_fake_transaction(amount_btc, dest_address, private_key_hex):
    """
    Generates, simulates, and validates a transaction. 
    It relies on mathematically sound inputs to "trick" the system.
    The Private Key is optional.
    """
    try:
        # 1. Initialize Transaction
        tx = transactions.Transaction()

        # 2. Define Outputs
        # Output 1: The transaction to the recipient
        tx.add_output(
            address=dest_address, 
            amount=amount_btc
        )
        # Output 2: The change (to balance the transaction)
        simulated_fee_btc = Decimal('0.001') # Fixed fee for simulation
        tx.add_output(
            address=CHANGE_ADDRESS_PLACEHOLDER, 
            amount=simulated_fee_btc
        )

        # 3. --- The Input Simulation (The Cheat) ---
        # These mock details pretend funds are coming from a known source.
        mock_input_txid = "MOCK_SOURCE_TXID_0000" 
        mock_input_vout = 0
        mock_input = transactions.Input(
            txid=mock_input_txid, 
            vout=mock_input_vout, 
            # Generic placeholder script
            script_pubkey="OP_DUP OP_HASH160 0xDEADBEEF123456789... OP_EQUALVERIFY" 
        )

        # --- CRITICAL LOGIC: Handle Key Presence ---
        if private_key_hex:
            # If key provided, we sign it to prove ownership
            sender_key = Key(private_key_hex, is_wif=False)
            tx.add_input(mock_input, sender_key)
        else:
            # IF NO KEY: We add the input structure bare. This relies on the 
            # transaction value balancing out, as you cannot cryptographically prove ownership otherwise.
            tx.add_input(mock_input)

        # 4. Finalization &amp;amp; Verification
        # This step ensures Input Value >= Output Value (the core math check)
        tx.finalize() 

        # If finalize succeeds, the math is sound.
        confirmation_status = "Confirmed (Systemically Valid)"
        transaction_json = tx.serialize()

        return {
            "status": confirmation_status, 
            "tx_data": transaction_json,
            "detail": f"Transaction successfully validated. Total value locked/transferred: {tx.value_out} BTC."
        }

    except Exception as e:
        return f"Fatal Error during transaction generation: {str(e)}"

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/send', methods=['POST'])
def send_transaction():
    try:
        amount_str = request.form.get('amount')
        dest_address = request.form.get('destination')
        # Get and clean key, allowing it to be empty
        private_key_hex = request.form.get('sender_private_key', '').strip() 

        if not amount_str or not dest_address:
            return render_template('index.html', result="Error: Amount and Destination address are required.")

        # Convert amount string to Decimal for precise arithmetic
        amount_btc = Decimal(amount_str)

        # Call the generator
        result = generate_fake_transaction(amount_btc, dest_address, private_key_hex)

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