from flask import Flask, render_template, request, redirect, url_for, flash
from pycoin import Transaction, Script, UTXO, TransactionBuilder
from pycoin.address import Address

app = Flask(__name__)
# Secret key needed for session management and flashing messages
app.secret_key = 'your_very_secret_key_here_change_this' 

# --- Configuration ---
# IMPORTANT: You need a private key/wallet that you control to sign the transactions.
# For maximum fake-ness, you might use a dedicated generator key.
# Replace this with your actual signing key/seed management.
SIGNING_PRIVATE_KEY = 'YOUR_PRIVATE_KEY_FOR_SIGNING' 
# Address to send the funds FROM (where the BTC is currently held)
SENDER_WALLET_ADDRESS = 'YOUR_SENDER_WALLET_ADDRESS'
# Address to send the funds TO (where the fake BTC is going)
# This will be provided by the user via the form.

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            amount_btc = float(request.form['amount'])
            recipient_address = request.form['recipient_address'].strip()

            if not amount_btc > 0:
                flash("Amount must be greater than zero.", 'error')
                return redirect(url_for('index'))
            if not recipient_address:
                flash("Recipient address cannot be empty.", 'error')
                return redirect(url_for('index'))

            # 1. Convert BTC amount to Satoshis (smallest unit)
            amount_sats = int(amount_btc * 100_000_000)

            # 2. Core Logic: Building the Transaction

            # For simplicity, we assume we are generating a transaction where:
            # Input Value = Target Amount + Fees (We aim for a fixed fee or adjust the input value)

            # --- Placeholder/Mocking UTXO finding ---
            # In a real scenario, you query the blockchain node to find UTXOs summing up to AT LEAST the desired amount + fee.
            # For this fake sender, we assume we find one input source (UTXO) large enough.

            # Mock UTXO details (You MUST replace these with real data found via a node RPC/API call)
            mock_utxo_value = 20000000 # Example: 0.02 BTC available

            # Calculate the required input amount to cover the output + fee
            # Let's assume a target fee of 0.001 BTC (100,000 satoshis)
            fee_sats = 100000

            # Input value must cover the desired amount + the fee
            input_value_sats = amount_sats + fee_sats

            if mock_utxo_value < input_value_sats:
                 flash(f"Mock UTXO value ({mock_utxo_value/10**8} BTC) is not enough to cover the desired amount ({amount_btc} BTC) plus fees.", 'error')
                 return redirect(url_for('index'))

            # Initialize the Transaction Builder
            tx = TransactionBuilder()

            # Add the input (This is the UTXO you are spending)
            # You need the TXID and output index of the UTXO you are spending.
            # For this example, we use placeholders:
            input_script_details = {'txid': 'FAKE_UTXO_TXID', 'vout': 0} 
            tx.add_input(input_script_details, value=mock_utxo_value)

            # Add the output (The recipient)
            output_txid = "FAKE_RECIPIENT_ADDRESS_GENERATED_TXID" # This will be generated once broadcasted
            output_script_details = {'address': recipient_address}
            tx.add_output(output_script_details, value=amount_sats)

            # Add change output (If the input was larger than the required output + fee)
            change_sats = mock_utxo_value - (amount_sats + fee_sats)
            if change_sats > 0:
                change_output_script_details = {'address': SENDER_WALLET_ADDRESS} # Send change back to self
                tx.add_output(change_output_script_details, value=change_sats)

            # 3. Signing (Requires the private key associated with the input UTXO)
            # In a real app, you must use the specific private key corresponding to the input UTXO.
            # For simplicity, we sign everything with one master key:

            # --- Signing Implementation Detail ---
            # Pycoin handles signing internally when you provide the required components.
            # You would typically use a library integration to sign the transaction structure.
            try:
                # Note: pycoin methods can be complex; this is a simplification.
                signed_tx = tx.sign(private_key=SIGNING_PRIVATE_KEY)

                # 4. Finalization (This is where you'd call the node RPC to broadcast)
                # broadcast_tx = node_client.send_raw_transaction(signed_tx.raw_transaction)

                flash(f"Success! Transaction constructed for {amount_btc} BTC sent to {recipient_address}.", 'success')

                # Return the raw transaction hex string or object for the user to verify/broadcast manually
                return render_template('index.html', 
                                       transaction_data=signed_tx.serialize(), 
                                       amount=amount_btc, 
                                       recipient=recipient_address)

            except Exception as e:
                flash(f"Error during transaction signing or building: {str(e)}", 'error')
                return redirect(url_for('index'))

        except ValueError:
            flash("Invalid input. Please ensure the amount is a number.", 'error')
        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", 'error')

    return render_template('index.html')

if __name__ == '__main__':
    # For Railway deployment, the command will be "gunicorn app:app"
    app.run(debug=True)