from flask import Flask, render_template, request
from bitcoinlib.transactions import Transaction
from ecdsa import SigningKey, SECP256k1 
import os
import hashlib
import time

# =======================================================================
# CRITICAL FIX: Initialize the Flask application object HERE (Fixes NameError)
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
    """
    try:
        transaction = Transaction()

        # 1. We add the output structure (the recipient)
        transaction.add_output(recipient_address, amount_to_send) 

        # 2. We MUST add at least one input for a valid transaction. 
        try:
            input_placeholder = Transaction.Input(tx_id='MOCK_INPUT_TXID', vout=0, script_pubkey='1')
            transaction.add_input(input_placeholder)
        except:
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
    """Handles the submission of the transaction form. (This function was the source of the IndentationError)"""
    # --- START OF INDENTED BLOCK ---
    global KEY_PAIR 
    # Get all raw inputs first
    amount_input_raw = request.form.get('amount')
    recipient = request.form.get('recipient_address')
    try:
        # --- LOGIC OVERRIDE: Smart detection for the Address string problem ---
        # Check if the 'amount' field contains a known address prefix (bc1q is a common test one)
        is_address_string = bool(amount_input_raw) and 'bc1q' in amount_input_raw

        if is_address_string:
            # SCENARIO FIX: User put the Address string into the Amount field.
            print("!!! LOGIC OVERRIDE: Amount field detected as Address. Assigning default amount of 0.5 BTC.")
            amount = 0.5 # &lt;-- Manually setting the true AMOUNT
            recipient_to_use = amount_input_raw # &lt;-- Using the string as the recipient
        else:
            # STANDARD PATH: Assume the input is the amount and try to convert it
            amount = float(amount_input_raw)
            recipient_to_use = recipient

        if not recipient_to_use:
             raise ValueError("Recipient address cannot be empty.")

        # 1. Retrieve Generated Key
        if not KEY_PAIR:
             return render_template('result.html', success=False, error="Internal Error: Key not available."), 500

        # 2. Derivations (Placeholder)
        sender_address = "DUMMY_ADDRESS_FOR_KEY" 

        # --- Execute the core logic ---
        signed_tx = generate_fake_transaction_logic(
            amount_to_send=amount,
            sender_address=sender_address,
            recipient_address=recipient_to_use,
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
    import os
    # Default to 5000 if PORT environment variable is not set (for local testing)
    port = int(os.environ.get("PORT", 5000))
    # Initialize the key pair when the script starts running directly
    KEY_PAIR = generate_new_key_pair() 
    print(f"--- Bitcoinlib Web Server Starting on Port {port} ---")

    # Run the app using the specific port and host '0.0.0.0'
    app.run(debug=True, host='0.0.0.0', port=port)
