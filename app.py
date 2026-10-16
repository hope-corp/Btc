from flask import Flask, render_template, request
from bitcoinlib import Transaction
from bitcoinlib.keys import Key
import json
from decimal import Decimal, getcontext
import os

app = Flask(__name__)

# Set precision high for financial calculations to handle BTC fractions accurately
getcontext().prec = 28

# --- Configuration ---
# Define a placeholder for the change address if the user doesn't specify one
CHANGE_ADDRESS_PLACEHOLDER = "ChangeAddressPlaceholder"

def generate_fake_transaction(amount_btc, dest_address, private_key_hex):
    """
    Generates, simulates, and validates a transaction. 
    It relies on mathematically sound inputs to "trick" the system.
    """
    try:
        # 1. Initialize Transaction
        tx = Transaction()

        # Fixed fee estimation for simulation
        simulated_fee_btc = Decimal('0.001') 
        total_value_out = amount_btc + simulated_fee_btc

        # 2. Add Outputs
        # Output 1: The transaction to the recipient
        tx.add_output(
            address=dest_address, 
            amount=amount_btc
        )
        # Output 2: The change (to balance the transaction)
        tx.add_output(
            address=CHANGE_ADDRESS_PLACEHOLDER, 
            amount=simulated_fee_btc
        )

        # 3. --- The Input Simulation (The Cheat) ---

        # We define mock inputs that represent the funds you claim to have.
        # IMPORTANT: These values (txid, vout) MUST point to real UTXOs in a real-world scenario.
        mock_input_txid = "MOCK_SOURCE_TXID_0000" 
        mock_input_vout = 0

        # Initialize the mock input structure
        mock_input = bitcoinlib.Input(
            txid=mock_input_txid, 
            vout=mock_input_vout, 
            # Generic placeholder script to allow the math to pass if no key is known
            script_pubkey="OP_DUP OP_HASH160 0xDEADBEEF123456789... OP_EQUALVERIFY" 
        )

        # Add input and sign if private key is provided
        if private_key_hex:
            sender_key = Key(private_key_hex, is_wif=False)
            tx.add_input(mock_input, sender_key)
        else:
            # If no private key, we add the input structure bare, relying on the library's 
            # ability to accept an unsigned/generic input based on the value it represents.
            tx.add_input(mock_input)

        # 4. Finalization & Verification
        # This step forces the internal math check: Input Value >= Output Value
        tx.finalize() 

        # If finalize succeeds, the math is sound, making it look real.
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
        private_key_hex = request.form.get('sender_private_key', '') # Default to empty string

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
    # Configures the server to run on the port specified by the environment (essential for Railway)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)