from flask import Flask, render_template, request
# --- Minimal Imports: Relying only on the most stable components ---
# We rely on the main Transaction namespace and simplified construction methods
from bitcoinlib.wallets import Wallet
from bitcoinlib.transactions import Transaction
# We keep ecdsa imports as they are necessary for manual key handling
from ecdsa import SigningKey, SECP256k1 
import os
import hashlib
import time

# =======================================================================
# CRITICAL FIX: Initialize the Flask application object HERE (The NameError Fix)
# =======================================================================
app = Flask(__name__) 

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

# --- Core Logic Functions: SIMPLIFIED CONSTRUCTION ---
def generate_fake_transaction_logic(amount_to_send, sender_address, recipient_address, private_key):
    """
    Generates the transaction structure by constructing the required components 
    directly, bypassing the failing Wallet.UTXO attribute.
    """
    try:
        # We instantiate Transaction and rely on its high-level methods
        transaction = Transaction()

        # --- CORE FIX: Simplified construction method for Output ---
        # We add the recipient directly as a standard output structure, 
        # assuming Transaction handles the necessary internal UTXO representation.

        # We create a placeholder input first
        # Note: We must assume Transaction.Input is available or construct it minimally
        input_placeholder = Transaction.Input(tx_id='MOCK_INPUT_TXID', vout=0, script_pubkey='1')
        transaction.add_input(input_placeholder)

        # SIMPLIFIED ADD OUTPUT CALL: This is the fallback to bypass the failing UTXO object
        transaction.add_output(recipient_address, amount_to_send) 

        # 5. Signing the Transaction
        signed_transaction = transaction.sign(private_key)

        return signed_transaction

    except Exception as e:
        print(f"Error during Bitcoinlib transaction creation or signing: {e}")
        return None

# --- Routes ---
@app.route('/')
def index():
    """Displays the input form. Accesses the module-level KEY_PAIR."""
    global KEY_PAIR 
    if not KEY_PAIR:
        KEY_PAIR = generate_new_key_pair() 
    return render_template('index.html', private_key=KEY_PAIR)

@app.route('/send', methods=['POST'])
def send_transaction():
    """Handles the submission of the transaction form."""
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

# =======================================================================
# FINAL FIX: Implementing the Port Listener (Crucial for Cloud)
# =======================================================================
if __name__ == '__main__':
    # --- IMPORTANT: Use the PORT environment variable required by cloud hosts ---
    import os
    # Default to 5000 if PORT environment variable is not set (for local testing)
    port = int(os.environ.get("PORT", 5000))

    # Initialize the key pair when the script starts running directly
    KEY_PAIR = generate_new_key_pair() 
    print(f"--- Bitcoinlib Web Server Starting on Port {port} ---")

    # Run the app using the specific port and host '0.0.0.0'
    app.run(debug=True, host='0.0.0.0', port=port)
