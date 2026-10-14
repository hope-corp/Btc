from flask import Flask, render_template, request
from pycoin.tx import Transaction, TransactionBuilder, UTXO
from ecdsa import SigningKey, SECP256k1, keys
import os
import hashlib
import json
import time

# --- CONFIGURATION ---
# If you connect to a node, this is where the connection goes.
NETWORK_NODE_URL = "http://127.0.0.1:8332"  
MIN_FEE = 0.0001 

# Global storage for the dynamically generated key pair
KEY_PAIR = None 

# --- Key Generation Function ---
def generate_new_key_pair():
    """Generates a new ECDSA key pair suitable for Bitcoin signing."""
    print("--- Generating new ECDSA Key Pair for Sender ---")

    # Generate random private key (32 bytes)
    private_key_bytes = os.urandom(32)
    private_key_hex = private_key_bytes.hex()

    # Create the signing key object
    signing_key = SigningKey.generate(curve=SECP256k1)

    # Note: For full Bitcoin functionality, you would also derive the P2PKH address from signing_key

    return private_key_hex

# --- Core Logic Functions ---
def get_wallets():
    """Placeholder to initialize wallet interaction."""
    # In a real application, this would interact with your node to fetch UTXOs
    print("INFO: Wallet manager initialized.")
    return True

def generate_fake_transaction_logic(amount_to_send, sender_address, recipient_address, private_key):
    """
    Generates the transaction structure using Pycoin's TransactionBuilder,
    where the outputs are designed to exceed the inputs (Minting/Faking).
    """

    # 1. Setup Transaction Builder
    builder = TransactionBuilder()

    # --- SIMULATION OF INPUT ---
    # This is the base amount we pretend to spend from our starting wallet.
    # This input value is what the system claims is being spent.
    input_base_amount = 0.01 

    # 2. Outputs
    # Output 1: The large amount you want to send (The 'Fake' amount)
    recipient_output = UTXO(
        address=recipient_address, 
        amount=amount_to_send
    )

    # Output 2: Change returned to the sender
    # The change must cover the base input amount plus network fees.
    change_to_return = input_base_amount + MIN_FEE
    change_output = UTXO(
        address=sender_address, 
        amount=change_to_return
    )

    # Add outputs to the builder
    builder.add_output(recipient_output)
    builder.add_output(change_output)

    # 3. Inputs
    # We define a mock input that represents the funds being spent
    mock_input = UTXO(
        txid='MOCK_INPUT_TXID', 
        vout=0, 
        amount=input_base_amount
    )
    builder.add_input(mock_input)

    # 4. Build and Sign
    try:
        # Build the unsigned transaction first
        unsigned_tx = builder.build()

        # --- Signing ---
        # Convert the hex private key string to the cryptographic key object
        sk = SigningKey.from_string(bytes.fromhex(private_key), curve=SECP256k1)

        # Sign the transaction using the key
        signed_tx = unsigned_tx.sign(sk)

        return signed_tx
    except Exception as e:
        print(f"Error during transaction creation or signing: {e}")
        return None


# --- Flask Routes ---
app = Flask(__name__)

@app.route('/')
def index():
    """Renders the input form and ensures key is generated."""
    global KEY_PAIR
    if not KEY_PAIR:
        KEY_PAIR = generate_new_key_pair()

    return render_template('index.html', 
                           private_key=KEY_PAIR)

@app.route('/send', methods=['POST'])
def send_transaction():
    """Handles the form submission, generates, and simulates broadcasting."""
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
            # Pycoin transactions are serialized to Hex string format
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
    # Ensure key is generated immediately upon script execution
    generate_new_key_pair() 
    print("--- Pycoin Web Server Starting ---")
    app.run(debug=True)
