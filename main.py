from web3 import exceptions
import os
from web3 import Web3
from web3.exceptions import ExtraDataLengthError
from dotenv import load_dotenv
from tqdm import tqdm


load_dotenv()

CELO_RPC_URL = os.environ.get("CELO_PROVIDER_URL")
CELO_PRIVATE_KEY = os.environ.get("CELO_DEPLOYER_PRIVATE_KEY")

# Connect to the Celo Alfajores testnet
w3 = Web3(Web3.HTTPProvider(CELO_RPC_URL))

# initialize account
deployer = w3.eth.account.from_key(CELO_PRIVATE_KEY)

print(f"Connected to Celo network. Address: {deployer.address}")

# Celo USD ABI
cUSD_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "from", "type": "address"},
            {"name": "to", "type": "address"},
            {"name": "value", "type": "uint256"}
        ],
        "name": "transferFrom",
        "outputs": [{"name": "", "type": "bool"}],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    }
]


def get_balance(account_address, contract_address, token="CELO"):
    # Get cUSD contract
    cusd_contract = w3.eth.contract(address=contract_address, abi=cUSD_ABI)

    if token == "CELO":
        return w3.from_wei(w3.eth.get_balance(account_address), 'ether')
    elif token == "cUSD":
        amount = cusd_contract.functions.balanceOf(account_address).call()
        balance = w3.from_wei(amount, 'ether')
        return balance    
    else:
        raise ValueError("Invalid token type")


def send_funds(account, to, amount, contract_address, token="CELO"):
    # Get cUSD contract
    cusd_contract = w3.eth.contract(address=contract_address, abi=cUSD_ABI)

    # Estimate gas required
    gas_estimate = cusd_contract.functions.transfer(to, w3.to_wei(amount, "ether")).estimate_gas(
        {"from": account.address}
    )

    if token == "CELO":
        transaction = {
            'to': to,
            'value': w3.to_wei(amount, 'ether'),
            'gas': gas_estimate,
            'gasPrice': w3.eth.gas_price,
            "nonce": w3.eth.get_transaction_count(account.address),
        }
        signed_tx = account.sign_transaction(transaction)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    elif token == "cUSD":
        transaction = cusd_contract.functions.transfer(to, w3.to_wei(amount, 'ether')).build_transaction({
            "from": account.address,
            "gas": gas_estimate,
            "gasPrice": w3.eth.gas_price,
            "nonce": w3.eth.get_transaction_count(account.address),
        })
        # Sign and send the transaction
        signed_transaction = account.sign_transaction(transaction)
        tx_hash = w3.eth.send_raw_transaction(
            signed_transaction.rawTransaction)
    else:
        raise ValueError("Invalid token type")

    # Wait for the transaction to be mined
    try:
        w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    except exceptions.TimeExhausted:
        print(
            f"Transaction with hash {tx_hash.hex()} was not mined within the given timeout.")

    return tx_hash



def get_transaction_history(address):
    transactions = []
    for i in tqdm(range(w3.eth.block_number, max(-1, w3.eth.block_number - 50), -1)):
        try:
            block = w3.eth.get_block(i, full_transactions=True)
        except ExtraDataLengthError:
            continue

        for tx in block.transactions:
            if tx['from'] == address or tx['to'] == address:
                transactions.append(tx)
    return transactions


# Example usage:
receiver_address = "0xcdd1151b2bC256103FA2565475e686346CeFd813"
amount_celo = 0.01
amount_cusd = 0.01
CUSD_ALFAJORES_CONTRACT_ADDRESS = "0x874069Fa1Eb16D44d622F2e0Ca25eeA172369bC1"


# Check CELO and cUSD balances
balance_celo = get_balance(deployer.address, CUSD_ALFAJORES_CONTRACT_ADDRESS, token="CELO")
balance_cusd = get_balance(deployer.address, CUSD_ALFAJORES_CONTRACT_ADDRESS, token="cUSD")
print(f"CELO balance: {balance_celo} CELO")
print(f"cUSD balance: {balance_cusd} cUSD")



# Send CELO and cUSD to the receiver
tx_hash_celo = send_funds(deployer, receiver_address, amount_celo, CUSD_ALFAJORES_CONTRACT_ADDRESS, token="CELO")
tx_hash_cusd = send_funds(deployer, receiver_address, amount_cusd,
                          CUSD_ALFAJORES_CONTRACT_ADDRESS, token="cUSD")
print(f"Sent {amount_celo} CELO to {receiver_address}. Transaction hash: {tx_hash_celo.hex()}")
print(f"Sent {amount_cusd} cUSD to {receiver_address}. Transaction hash: {tx_hash_cusd.hex()}")


# Fetch transaction history
transaction_history = get_transaction_history(deployer.address)
print("Transaction history:")
for tx in transaction_history:
    print(tx)


# Wait for the CELO and cUSD transactions to be mined
transaction_receipt_celo = w3.eth.wait_for_transaction_receipt(tx_hash_celo)
transaction_receipt_cusd = w3.eth.wait_for_transaction_receipt(tx_hash_cusd)
print("CELO transaction mined. Block number:",
      transaction_receipt_celo['blockNumber'])
print("cUSD transaction mined. Block number:",
      transaction_receipt_cusd['blockNumber'])


# Check updated CELO and cUSD balances
balance_celo_updated = get_balance(
    deployer.address, CUSD_ALFAJORES_CONTRACT_ADDRESS, token="CELO")
balance_cusd_updated = get_balance(
    deployer.address, CUSD_ALFAJORES_CONTRACT_ADDRESS, token="cUSD")
print(f"Updated CELO balance: {balance_celo_updated} CELO")
print(f"Updated cUSD balance: {balance_cusd_updated} cUSD")
