from flask import Flask, render_template, request
from bitcoinlib.transactions import Transaction
from ecdsa import SigningKey, SECP256k1 
import os
import hashlib
import time

app = Flask(__name__) 

NETWORK_NODE_URL = "http://127.0.0.1:8332"
MIN_FEE = 0.0001 
KEY_PAIR = None 

def generate_new_key_pair():
    """Generates a new ECDSA key pair suitable for Bitcoin signing."""
    print("--- Generating new ECDSA Key Pair for Sender ---")
    private_key_bytes = os.urandom(32)
    private_key_hex = private_key_bytes.hex()
    print(f"--- Key Pair Generated. Hex Private Key: {private_key_hex} ---")
    return private_key_hex

def generate_fake_transaction_logic(amount_to_send, sender_address, recipient_address, private_key):
    """
    Generates the transaction structure by relying on the Transaction object's core methods.
    """
    try:
        transaction = Transaction()
        transaction.add_output(recipient_address, amount_to_send) 
        try:
            input_placeholder = Transaction.Input(tx_id='MOCK_INPUT_TXID', vout=0, script_pubkey='1')
            transaction.add_input(input_placeholder)
        except:
            print("WARNING: Bypassing explicit Input object due to library incompatibility.")
        signed_transaction = transaction.sign(private_key)
        return signed_transaction
    except Exception as e:
        print(f"CRITICAL LIB ERROR: {e}")
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
    amount_input_raw = request.form.get('amount')
    recipient = request.form.get('recipient_address')

    try:
        is_address_string = bool(amount_input_raw) and 'bc1q' in amount_input_raw

        if is_address_string:
            print("!!! LOGIC OVERRIDE: Amount field detected as Address. Assigning default amount of 0.5 BTC.")
            amount = 0.5 
            recipient_to_use = amount_input_raw 
        else:
            amount = float(amount_input_raw)
            recipient_to_use = recipient

        if not recipient_to_use:
             return render_template('result.html', success=False, error="Recipient address cannot be empty."), 400

        if not KEY_PAIR:
             # This return is now guaranteed to be functional
             return render_template('result.html', success=False, error="Internal Error: Key not available."), 500

        sender_address = "DUMMY_ADDRESS_FOR_KEY" 

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
        return render_template('result.html', success=False, error=f"Validation Error: {ve}"), 400
    except Exception as e:
        return render_template('result.html', success=False, error=f"An unexpected system error occurred: {e}"), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    KEY_PAIR = generate_new_key_pair() 
    print(f"--- Bitcoinlib Web Server Starting on Port {port} ---")
    app.run(debug=True, host='0.0.0.0', port=port)
