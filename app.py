from flask import Flask, render_template, request
# --- CRITICAL FIX APPLIED: Changed Keys to keys ---
from bitcoinlib.wallets import Wallet
from bitcoinlib.transactions import Transaction
# Import 'keys' as suggested by the error message
from bitcoinlib.keys import keys 
from bitcoinlib.util import decode_hex
from ecdsa import SigningKey, SECP256k1
import os
import hashlib
import time

# --- CONFIGURATION ---
NETWORK_NODE_URL = "http://127.0.0.1:8332"  
MIN_FEE = 0.0001 

# Global storage for the dynamically generated key pair
KEY_PAIR = None 

# --- Key Generation Function ---
def generate_new_key_pair():
    """Generates a new ECDSA key pair suitable for Bitcoin signing."""
    print("--- Generating new ECDSA Key Pair for Sender ---")
    private_key_bytes = os.urandom(32)
    private_key_hex = private_key_bytes.hex()
    print(f"--- Key Pair Generated. Hex Private Key: {private_key_hex} ---")
    return private_key_hex

# --- Core Logic Functions ---
def generate_fake_transaction_logic(amount_to_send, sender_address, recipient_address, private_key):
    """
    Generates the transaction structure using Bitcoinlib, creating a 'fake'
    input (UTXO) and spending it to the recipient.
    """
    try:
        # We use a manual transaction build approach for the 'fake' input scenario
        transaction = Transaction()

        # 2. Outputs: The funds going to the recipient (The 'Fake' amount)
        recipient_utxo = bitcoinlib.UTXO(
            address=recipient_address, 
            value=amount_to_send
        )

        # 3. Inputs: The funds being spent (Placeholder Input)
        input_placeholder = bitcoinlib.Input(
            tx_id='MOCK_INPUT_TXID', 
            vout=0, 
            script_pubkey='1' # Placeholder script
        )

        # 4. Transaction Builder Setup
        transaction.add_input(input_placeholder)
        transaction.add_output(recipient_utxo)

        # 5. Signing the Transaction
        signed_transaction = transaction.sign(private_key)

        return signed_transaction

    except Exception as e:
        print(f"Error during Bitcoinlib transaction creation or signing: {e}")
        return None

@app.route('/')
def index():
    """Displays the input form. Accesses the module-level KEY_PAIR."""
    global KEY_PAIR # Explicitly state we are using the module-level variable
    if not KEY_PAIR:
        KEY_PAIR = generate_new_key_pair() 
    return render_template('index.html', private_key=KEY_PAIR)

@app.route('/send', methods=['POST'])
def send_transaction():
    """Handles the submission of the transaction form."""
    global KEY_PAIR # Explicitly state we are using the module-level variable

    try:
        amount = float(request.form['amount'])
        recipient = request.form['recipient_address']

        # 1. Retrieve Generated Key
        if not KEY_PAIR:
             return render_template('result.html', success=False, error="Internal Error: Key not available."), 500

        # 2. Derivations (Placeholder)
        sender_address = "DUMMY_ADDRESS_FOR_KEY" 

        # --- Execute the core logic ---
        signed_tx = generate_fake_transaction_logic(
            amount_to_send=amount,
            sender_address=sender_address,
            recipient_address=recipient,
            private_key=KEY_PAIR
        )

        if signed_tx:
            # Bitcoinlib provides serialization methods directly
            tx_hex = signed_tx.serialize_hex() 
            return render_template('result.html', 
                                   success=True, 
                                   tx_data=tx_hex,
                                   amount_sent=amount,
                                   private_key=KEY_PAIR)
        else:
            return render_template('result.html', success=False, error="Failed to generate or sign the transaction."), 500

    except ValueError:
        return render_template('result.html', success=False, error="Invalid amount entered."), 400
    except Exception as e:
        return render_template('result.html', success=False, error=f"An unexpected error occurred: {e}"), 500

if __name__ == '__main__':
    # Initialize the key pair when the script starts running directly
    KEY_PAIR = generate_new_key_pair() 
    print("--- Bitcoinlib Web Server Starting ---")
    app.run(debug=True)
