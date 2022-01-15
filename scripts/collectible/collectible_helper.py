import subprocess
import os

def deploy_collectible(collection_name, collection_symbol):
    cmd = ["brownie", "run", "scripts/collectible/deploy_collectible.py", "main", collection_name, collection_symbol, "--network", "rinkeby"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    output, error = process.communicate()
    print(output, error)
    return output, error

def create_collectible(nft_type, description, image_path, attributes, receiver):
    attributes_string = f'{attributes["company_name"]}|{attributes["company_symbol"]}|{attributes["timestamp"]}|{attributes["number_of_shares"]}'

    if nft_type == 'genesis':
        operation_name = f'Genesis Create {attributes["number_of_shares"]} Shares'
    elif nft_type == 'issue':
        operation_name = f'Issue {attributes["number_of_shares"]} Shares'
    else:
        operation_name = f'Burn {attributes["number_of_shares"]} Shares'

    cmd = ["brownie", "run", "scripts/collectible/create_collectible.py", "main", nft_type, operation_name, description, image_path, attributes_string, receiver, "--network", "rinkeby"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    output, error = process.communicate()
    print(output, error)
    return output, error

def burn_collectible(token_id):
    cmd = ["brownie", "run", "scripts/collectible/burn_collectible.py", "main", token_id, "--network", "rinkeby"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    output, error = process.communicate()
    print(output, error)
    return output, error
