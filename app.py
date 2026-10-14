from flask import Flask, render_template, request
# --- CRITICAL CHANGE: SWAPPING PYCOIN FOR BITCOINLIB ---
# Import necessary components from bitcoinlib
from bitcoinlib.wallets import Wallet
from bitcoinlib.transactions import Transaction
from bitcoinlib.keys import Keys
from bitcoinlib.util import decode_hex
# ---------------------------------------------------
from ecdsa import SigningKey, SECP256k1, keys # Still useful for low-level keys if needed
import os
import hashlib
import time

# --- CONFIGURATION ---
# Note: Bitcoinlib might use different node access methods; we keep the placeholder.
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

    # 1. Setup: Initialize Wallet/Transaction structure
    # Bitcoinlib typically manages this through a Wallet object or manually

    try:
        # A simple way to start: Create a new transaction instance
        # We use the private_key to simulate the input source
        wallet = Wallet.create_wallet("mock_wallet", {'keys': {private_key: None}})

        # --- TRANSACTION BUILDING (Bitcoinlib Style) ---

        # 2. Outputs: The funds going to the recipient (The 'Fake' amount)
        # Bitcoinlib handles UTXO creation based on addresses and amounts
        recipient_utxo = bitcoinlib.UTXO(
            address=recipient_address, 
            value=amount_to_send
        )

        # 3. Inputs: The funds being spent (The 'Fake' input we are generating)
        # Since we are 'faking' the input, we simulate an existing input source.
        # For a true fake input, you'd need real UTXOs, but for simplicity, we define a placeholder input.

        # For this 'fake' scenario, we create a mock input to be spent
        input_placeholder = bitcoinlib.Input(
            tx_id='MOCK_INPUT_TXID', 
            vout=0, 
            script_pubkey='1' # Placeholder script
        )

        # 4. Transaction Builder Setup
        transaction = Transaction()
        transaction.add_input(input_placeholder)
        transaction.add_output(recipient_utxo)

        # Add change (which is implicitly handled or needs manual calculation/adjustment)
        # For simplicity in a fake scenario, we are NOT calculating change rigorously here, 
        # but an advanced version would add change_output = UTXO(...) and adjust fees.

        # 5. Signing the Transaction
        # We use the private key to sign the transaction
        signed_transaction = transaction.sign(private_key)

        return signed_transaction

    except Exception as e:
        print(f"Error during Bitcoinlib transaction creation or signing: {e}")
        return None

@app.route('/')
def index():
    global KEY_PAIR
    if not KEY_PAIR:
        KEY_PAIR = generate_new_key_pair()
    return render_template('index.html', private_key=KEY_PAIR)

@app.route('/send', methods=['POST'])
def send_transaction():
    global KEY_PAIR

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
    global KEY_PAIR
    KEY_PAIR = generate_new_key_pair() 
    print("--- Bitcoinlib Web Server Starting ---")
    app.run(debug=True)
