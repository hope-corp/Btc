from flask import Flask, render_template, request, redirect, url_for, flash
from pycoin import Transaction, TransactionBuilder
import requests
import json

app = Flask(__name__)
app.secret_key = 'your_very_secret_key_here_change_this' 

# --- Configuration ---
RPC_URL = "https://bitcoin-rpc.publicnode.com" # Using the provided URL
SIGNING_PRIVATE_KEY = 'YOUR_PRIVATE_KEY_FOR_SIGNING' 
SENDER_WALLET_ADDRESS = 'YOUR_SENDER_WALLET_ADDRESS' # Address that owns the keys
# ---------------------

# Helper function to handle RPC communication
def call_rpc(method, params=None):
    try:
        response = requests.post(
            f"{RPC_URL}/jsonrpc", 
            json={"jsonrpc": "2.0", "method": method, "params": params or [], "id": 1}
        )
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        if 'result' in data:
            return data['result']
        return None
    except requests.exceptions.RequestException as e:
        print(f"RPC Request Error: {e}")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            amount_btc = float(request.form['amount'])
            recipient_address = request.form['recipient_address'].strip()

            if not amount_btc &gt; 0 or not recipient_address:
                flash("Please provide valid amount and recipient.", 'error')
                return redirect(url_for('index'))

            amount_sats = int(amount_btc * 100_000_000)

            # --- Step 1: Find UTXOs (Inputs) ---
            # This requires finding unspent outputs for the SENDER_WALLET_ADDRESS
            print("Fetching UTXOs...")

            # RPC call to get UTXOs for the sender
            utxo_response = call_rpc('getrawbalance', [SENDER_WALLET_ADDRESS]) # Simplified, real one is getunspent
            # NOTE: getrawbalance only gives total balance. A proper implementation needs 'spv_get_unspent' or similar.
            # For this example, we must rely on the structure:

            # --- Mocking UTXO selection for demonstration ---
            # In a real scenario, you'd loop through UTXOs until they cover the target + fee.
            # Since we don't have a full UTXO finder built-in, we hardcode the ideal inputs for now:

            # Mock inputs needed to cover the desired amount + fee (e.g., 1 BTC input is used)
            mock_input_value = 100000000 # 1 BTC available in the input
            input_script_details = {'txid': 'MOCK_INPUT_TXID', 'vout': 0} 

            # --- Step 2: Building the Transaction ---
            tx = TransactionBuilder()
            tx.add_input(input_script_details, value=mock_input_value)

            # Set desired output value (the "fake" amount)
            target_output_value = amount_sats

            # Set change output (Input - Target Output - Fee)
            # Assuming a fixed fee of 50,000 sats for this example
            fixed_fee = 50000
            change_sats = mock_input_value - target_output_value - fixed_fee

            # Add Recipient Output
            tx.add_output({'address': recipient_address}, value=target_output_value)

            # Add Change Output (back to sender)
            if change_sats &gt; 0:
                 tx.add_output({'address': SENDER_WALLET_ADDRESS}, value=change_sats)

            # --- Step 3: Signing ---
            try:
                signed_tx = tx.sign(private_key=SIGNING_PRIVATE_KEY)
            except Exception as e:
                flash(f"Error during transaction signing: {str(e)}. Check your private key and UTXO validity.", 'error')
                return redirect(url_for('index'))

            # --- Step 4: Broadcast to Confirm ---
            raw_tx = signed_tx.serialize()
            print("Broadcasting transaction...")

            # RPC call to broadcast the transaction
            broadcast_response = call_rpc('sendrawtransaction', [raw_tx])

            if broadcast_response and 'result' in broadcast_response and broadcast_response['result'] == 'true':
                # Success! The transaction is in the mempool
                flash(f"SUCCESS! {amount_btc} BTC sent to {recipient_address} and confirmed in the mempool!", 'success')
                return render_template('index.html', 
                                       transaction_data=raw_tx, 
                                       amount=amount_btc, 
                                       recipient=recipient_address)
            else:
                # Node rejected it, or connection failed
                flash(f"Failed to broadcast transaction. Node response: {broadcast_response}", 'error')
                return render_template('index.html', 
                                       transaction_data=raw_tx, 
                                       amount=amount_btc, 
                                       recipient=recipient_address)


        except ValueError:
            flash("Invalid input. Please ensure the amount is a number.", 'error')
        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", 'error')

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)