from flask import Flask, render_template, request, redirect, url_for
import bitcoinlib.wallets as wallet
import bitcoinlib.transactions as tx
from bitcoinlib.keys import Key
import json
import os
from ecdsa import SigningKey, SECP256k1, keys
import hashlib

app = Flask(__name__)

# --- CONFIGURATION ---
NETWORK_NODE_URL = "http://127.0.0.1:8332"  # Node or API endpoint
MIN_FEE = 0.0001 

# Global storage for the dynamically generated key pair
KEY_PAIR = None 

# --- Key Generation Function ---
def generate_new_key_pair():
    """Generates a new ECDSA key pair suitable for Bitcoin signing."""
    print("--- Generating new ECDSA Key Pair for Sender ---")

    # Generate a new random private key (32 bytes)
    private_key_bytes = os.urandom(32)

    # Create the signing key object
    signing_key = SigningKey.generate(curve=SECP256k1)

    # In a real implementation, you would use bitcoinlib's methods to derive the address 
    # from the public key bytes. For simplicity here, we focus on the signing ability.

    # We store the raw private key for signing by bitcoinlib
    return private_key_bytes.hex()


# --- Core Logic Functions ---

def initialize_key_pair():
    """Checks if a key exists, or generates a new one."""
    global KEY_PAIR
    if KEY_PAIR is None:
        KEY_PAIR = generate_new_key_pair()
        print(f"Successfully generated and stored sender key.")
        return KEY_PAIR
    return KEY_PAIR

def get_wallet_info():
    """Initializes or returns the wallet object needed for UTXO management."""
    try:
        # Initialize wallet interaction with the network
        return True
    except Exception as e:
        print(f"Error initializing wallet: {e}")
        return False

def generate_fake_transaction_logic(amount_to_send, sender_address, recipient_address, private_key):
    """
    Generates the transaction structure based on the 'faking' principle, signed 
    using the dynamically generated private key.
    """

    # --- SIMULATION OF INPUT ---
    # Input Base: The amount you pretend to spend from your wallet
    input_base_amount = 0.01 

    # 1. Inputs (What we are spending)
    inputs = [
        tx.Input(
            txid='MOCK_INPUT_TXID', 
            vout=0, 
            script_pubkey='MOCK_SCRIPT_PUBKEY'
        )
    ]

    # 2. Outputs
    # Output 1: The large amount you want to send (The 'Fake' amount)
    recipient_output = tx.Output(
        address=recipient_address, 
        amount=amount_to_send
    )

    # Output 2: Change returned to the sender
    change_to_return = input_base_amount + MIN_FEE
    change_output = tx.Output(
        address=sender_address, 
        amount=change_to_return
    )

    outputs = [recipient_output, change_output]

    # 3. Transaction Object Creation
    new_tx = tx.Transaction(inputs=inputs, outputs=outputs)

    # 4. Signing (Crucial step: using the generated key)
    try:
        # We pass the private key string directly to the signer
        new_tx.sign(
            private_key=private_key, 
            network=NETWORK_NODE_URL
        )
        return new_tx
    except Exception as e:
        print(f"Error during transaction signing: {e}")
        return None


# --- Flask Routes ---

@app.route('/')
def index():
    """Renders the input form."""
    # Ensure key is generated before showing the form
    if not initialize_key_pair():
        return "Fatal Error: Could not initialize wallet/key pair.", 500

    return render_template('index.html', 
                           private_key=KEY_PAIR)

@app.route('/send', methods=['POST'])
def send_transaction():
    """Handles the form submission, generates, and simulates broadcasting."""

    try:
        amount = float(request.form['amount'])
        recipient = request.form['recipient_address']

        # 1. Retrieve Generated Key
        generated_private_key = KEY_PAIR

        # 2. Derivations (In a real scenario, you must calculate this from the key)
        # Since bitcoinlib doesn't expose simple derivation helpers easily without full node access,
        # we use a placeholder for the sender address derived from the key.
        sender_address = "DUMMY_ADDRESS_FOR_KEY" 

        # --- Execute the core logic ---
        signed_tx = generate_fake_transaction_logic(
            amount_to_send=amount,
            sender_address=sender_address,
            recipient_address=recipient,
            private_key=generated_private_key
        )

        if signed_tx:
            tx_json = signed_tx.to_json()
            return render_template('result.html', 
                                   success=True, 
                                   tx_data=tx_json,
                                   amount_sent=amount,
                                   private_key=generated_private_key)
        else:
            return render_template('result.html', success=False, error="Failed to generate or sign the transaction."), 500

    except ValueError:
        return render_template('result.html', success=False, error="Invalid amount entered."), 400
    except Exception as e:
        return render_template('result.html', success=False, error=f"An unexpected error occurred: {e}"), 500

if __name__ == '__main__':
    # Initialize the key pair immediately when the script starts
    initialize_key_pair() 
    app.run(debug=True)
