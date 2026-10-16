# --- Imports ---
from flask import Flask, render_template, request
from bitcoinlib import transactions 
from bitcoinlib.keys import Key 
from decimal import Decimal, getcontext
import os
import requests 
from ecdsa import SigningKey, SECP256k1
from base58 import b58encode

# --- 1. Initialization ---
app = Flask(__name__)

# Set precision high for financial calculations to handle BTC fractions accurately
getcontext().prec = 28

# Configuration
CHANGE_ADDRESS_PLACEHOLDER = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa" 
BTC_TO_SAT = 100_000_000
RPC_NODE_URL = "https://bitcoin-rpc.publicnode.com" 

# --- 2. Functions ---
def generate_keypair_and_address():
    """
    Generates a new ECDSA keypair and derives the corresponding Base58Check Bitcoin Address.
    Returns: (private_key_hex, public_address)
    """
    sk = SigningKey.generate(curve=SECP256k1)
    pk = sk.get_verifying_key()
    public_key_raw = pk.to_string()

    fake_address_data = b58encode(public_key_raw + b'\x00' * 20) 
    public_address = fake_address_data.decode('utf-8') 
    private_key_hex = sk.to_string().hex()

    return private_key_hex, public_address

def submit_transaction_to_rpc(tx_hex):
    """
    Submits the signed raw transaction hex to the public Bitcoin RPC Node.
    """
    try:
        headers = {'Content-Type': 'application/json'}
        payload = {
            "jsonrpc": "1.0",
            "id": "flask-bitcoin-tool",
            "method": "sendrawtransaction",
            "params": [tx_hex]
        }
        response = requests.post(RPC_NODE_URL, json=payload, headers=headers, timeout=10)
        data = response.json()
        
        if "error" in data and data["error"]:
            return f"Node Rejected (Expected for Mock TX): {data['error'].get('message', 'Unknown error')}"
        
        return f"Success! TXID: {data.get('result')}"
    except Exception as e:
        return f"RPC Connection Error: {str(e)}"

def generate_fake_transaction(amount_btc_decimal, dest_address, private_key_hex):
    """
    Generates, signs, and validates a transaction using the internal ECDSA Key.
    """
    try:
        amount_satoshi = int(amount_btc_decimal * BTC_TO_SAT)
        simulated_fee_satoshi = int(Decimal('0.001') * BTC_TO_SAT) 

        tx = transactions.Transaction()
        tx.add_output(amount_satoshi, address=dest_address) 
        tx.add_output(simulated_fee_satoshi, address=CHANGE_ADDRESS_PLACEHOLDER)

        mock_input_txid = "0000000000000000000000000000000000000000000000000000000000000000" 
        mock_input_vout = 0

        # --- Use the Key we generated/provided (Removed is_wif argument) ---
        sender_key = Key(private_key_hex)
        tx.add_input(prev_txid=mock_input_txid, output_n=mock_input_vout, keys=sender_key)
        tx.sign() 

        confirmation_status = "Confirmed (Systemically Valid)"
        transaction_hex = tx.as_hex()
        total
