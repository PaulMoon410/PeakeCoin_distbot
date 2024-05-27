from flask import Flask, request, jsonify
import os
import logging
from beem import Hive
from beem.account import Account
from beem.transactionbuilder import TransactionBuilder
from beem.instance import set_shared_blockchain_instance
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, filename='peakecoin_bot.log',
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration from environment variables
account_name = os.getenv('HIVE_ACCOUNT_NAME')
hive_active_key = os.getenv('HIVE_ACTIVE_KEY')
hive_posting_key = os.getenv('HIVE_POSTING_KEY')
token_symbol = os.getenv('TOKEN_SYMBOL', 'PEK')
minimum_balance = float(os.getenv('MINIMUM_BALANCE', 0))
reward_amount = float(os.getenv('REWARD_AMOUNT', 1))
memo = os.getenv('MEMO', 'Thanks for participating!')

if not account_name or not hive_active_key or not hive_posting_key:
    logging.error('Missing required environment variables')
    raise ValueError('Missing required environment variables')

# Initialize Hive instance with private keys
hive = Hive(keys=[hive_active_key, hive_posting_key])
set_shared_blockchain_instance(hive)

def transfer_token(recipient, amount, symbol, memo=""):
    try:
        account = Account(account_name)
        tx = TransactionBuilder()
        tx.append_transfer(recipient, amount, symbol, memo)
        tx.appendSigner(account, "active")
        tx.sign()
        tx.broadcast()
        logging.info(f'Transferred {amount} {symbol} to {recipient}')
    except Exception as e:
        logging.error(f'Error transferring tokens: {e}')
        raise

@app.route('/distribute', methods=['POST'])
def distribute_rewards():
    try:
        account = Account(account_name)
        for user in account.balances[token_symbol]['delegations']:
            if user['balance'] > minimum_balance:
                transfer_token(user['account'], reward_amount, token_symbol, memo)
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        logging.error(f'Error distributing rewards: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({'status': 'running'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
