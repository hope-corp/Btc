from flask import Flask, render_template, request
from bitcoinlib.transactions import Transaction
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

# --- Core Logic Functions: FINAL STABLE CONSTRUCTION ---
def generate_fake_transaction_logic(amount_to_send, sender_address, recipient_address, private_key):
    """
    Generates the transaction structure by relying on the Transaction object's core methods.
    This version assumes the 'amount_to_send' is a number and the rest are valid strings.
    """
    try:
        transaction = Transaction()

        # 1. We add the output structure (the recipient)
        transaction.add_output(recipient_address, amount_to_send) 

        # 2. We MUST add at least one input for a valid transaction. 
        try:
            # We retry the Input helper, as it's the most likely fix for the 'Input' attribute error
            input_placeholder = Transaction.Input(tx_id='MOCK_INPUT_TXID', vout=0, script_pubkey='1')
            transaction.add_input(input_placeholder)
        except:
            # Fallback: If Transaction.Input fails, we proceed with a minimalist transaction state 
            print("WARNING: Bypassing explicit Input object due to library incompatibility.")


        # 3. Signing the Transaction
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
        # --- CRITICAL FIX: Explicitly casting the amount is the source of the solution ---
        amount_input = request.form.get('amount')
        if not amount_input:
             raise ValueError("Amount field is empty.")

        # This line explicitly forces the string input to become a number (float)
        amount = float(amount_input) 

        recipient = request.form.get('recipient_address')

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
            tx_hex = signed_tx.serialize_hex() 
            return render_template('result.html', 
                                   success=True, 
                                   tx_data=tx_hex,
                                   amount_sent=amount,
                                   private_key=KEY_PAIR)
        else:
            return render_template('result.html', success=False, error="Failed to generate or sign the transaction."), 500

    except ValueError as ve:
        # This catches both empty fields and the string-to-float conversion errors
        return render_template('result.html', success=False, error=f"Validation Error: {ve}"), 400
    except Exception as e:
        # Catch all other deep library errors
        return render_template('result.html', success=False, error=f"An unexpected system error occurred: {e}"), 500

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
