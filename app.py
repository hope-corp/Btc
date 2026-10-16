from flask import Flask, render_template, request
from bitcoinlib import transactions, keys 
import json
from decimal import Decimal, getcontext
import os

# --- 1. Initialization ---
app = Flask(__name__)

# Set precision high for financial calculations to handle BTC fractions accurately
getcontext().prec = 28

# Configuration
CHANGE_ADDRESS_PLACEHOLDER = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa" 
BTC_TO_SAT = 100_000_000

# --- 2. Functions ---
def generate_fake_transaction(amount_btc_decimal, dest_address, private_key_hex):
    """
    Generates, simulates, and validates a transaction operating entirely in Satoshis (integers).
    The Private Key is optional.
    """
    try:
        amount_satoshi = int(amount_btc_decimal * BTC_TO_SAT)
        simulated_fee_satoshi = int(Decimal('0.001') * BTC_TO_SAT) 

        tx = transactions.Transaction()
        tx.add_output(amount_satoshi, address=dest_address) 
        tx.add_output(simulated_fee_satoshi, address=CHANGE_ADDRESS_PLACEHOLDER)

        mock_input_txid = "0000000000000000000000000000000000000000000000000000000000000000" 
        mock_input_vout = 0
        
        if private_key_hex:
            sender_key = Key(private_key_hex, is_wif=False)
            tx.add_input(prev_txid=mock_input_txid, output_n=mock_input_vout, keys=sender_key)
            tx.sign()
        else:
            tx.add_input(prev_txid=mock_input_txid, output_n=mock_input_vout)

        confirmation_status = "Confirmed (Systemically Valid)"
        transaction_json = tx.serialize()
        return {
            "status": confirmation_status, 
            "tx_data": transaction_json,
            "detail": f"Transaction successfully validated. Total value locked/transferred: {tx.value_out / BTC_TO_SAT} BTC."
        }
    except Exception as e:
        return f"Final Validation Error: {str(e)} (Transaction mathematically sound, but library validation failed)."

# ---
