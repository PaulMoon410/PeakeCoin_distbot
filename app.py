from flask import Flask, request, jsonify, render_template
import os
import logging
import requests
from beem import Hive
from beem.account import Account
from beem.instance import set_shared_blockchain_instance
from beem.account import PrivateKey
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG, filename='peakecoin_bot.log',
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration from environment variables
account_name = os.getenv('HIVE_ACCOUNT_NAME')
hive_active_key = os.getenv('HIVE_ACTIVE_KEY')
hive_posting_key = os.getenv('HIVE_POSTING_KEY')
token_symbol = os.getenv('TOKEN_SYMBOL', 'PeakeCoin')
minimum_balance = float(os.getenv('MINIMUM_BALANCE', 0))  # Convert to float
reward_amount = float(os.getenv('REWARD_AMOUNT', 1))  # Convert to float
memo = os.getenv('MEMO', 'Thanks for participating!')

if not account_name or not hive_active_key or not hive_posting_key:
    logging.error('Missing required environment variables')
    raise ValueError('Missing required environment variables')

# Debugging: Print keys
logging.debug(f"Active Key: {hive_active_key}")
logging.debug(f"Posting Key: {hive_posting_key}")

try:
    active_private_key = PrivateKey(hive_active_key)
    posting_private_key = PrivateKey(hive_posting_key)
    hive = Hive(keys=[active_private_key, posting_private_key])
    set_shared_blockchain_instance(hive)
except Exception as e:
    logging.error(f'Error initializing Hive instance: {e}')
    raise

def transfer_hive_engine_token(recipient, amount, symbol, memo=""):
    url = "https://api.hive-engine.com/rpc/contracts"
    payload = {
        "jsonrpc": "2.0",
        "method": "find",
        "params": {
            "contract": "tokens",
            "table": "balances",
            "query": {
                "symbol": symbol,
                "account": account_name
            },
            "limit": 1,
            "offset": 0,
            "indexes": []
        },
        "id": 1
    }
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        logging.debug(f'Balance query response: {response.text}')
        if response.status_code == 200:
            data = response.json()
            balance = float(data['result'][0]['balance'])
            logging.debug(f'Current balance for {symbol}: {balance}')
            if balance >= amount:
                transfer_payload = {
                    "jsonrpc": "2.0",
                    "method": "transfer",
                    "params": {
                        "contract": "tokens",
                        "from": account_name,
                        "to": recipient,
                        "symbol": symbol,
                        "quantity": str(amount),
                        "memo": memo
                    },
                    "id": 1
                }
                transfer_response = requests.post(url, json=transfer_payload, headers=headers)
                logging.debug(f'Transfer response: {transfer_response.text}')
                if transfer_response.status_code == 200:
                    transfer_data = transfer_response.json()
                    logging.debug(f'Transfer response data: {transfer_data}')
                    if 'error' not in transfer_data:
                        logging.info(f'Transferred {amount} {symbol} to {recipient}')
                        return True
                    else:
                        logging.error(f'Transfer error: {transfer_data["error"]}')
                        return False
                else:
                    logging.error(f'Error transferring tokens: {transfer_response.text}')
                    return False
            else:
                logging.error(f'Insufficient balance: {balance} {symbol}')
                return False
        else:
            logging.error(f'Error fetching balance: {response.text}')
            return False
    except Exception as e:
        logging.error(f'Error in Hive-Engine API request: {e}')
        return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/distribute', methods=['POST'])
def distribute_rewards():
    try:
        data = request.json
        recipient = data.get('recipient')
        amount = float(data.get('amount', reward_amount))  # Convert to float
        success = transfer_hive_engine_token(recipient, amount, token_symbol, memo)
        if success:
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Transfer failed'}), 500
    except Exception as e:
        logging.error(f'Error distributing rewards: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({'status': 'running'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
