import subprocess
import os
from datetime import datetime as dt
import uuid
import json

def deploy_collectible(collection_name, collection_symbol, member_account, min_signature, image_path):
    def _pin_to_IPFS(filename):
        ipfs_handler_path = './scripts/IPFS/ipfs_handler.js'
        cmd = os.popen(f'node -e \'require("{ipfs_handler_path}").ipfs_pin_file("{filename}")\'')
        result = cmd.read()
        cmd.close()
        return result
    image_hash = _pin_to_IPFS(image_path)
    if len(image_hash) != 47:
        print('Error occured when pinning image to ipfs.')
        print(image_hash)
        return
    image_hash = image_hash[:-1]

    attributes = [
            {'trait_type': 'Company Name', 'value': collection_name},
            {'trait_type': 'Company Symbol', 'value': collection_symbol},
            {'trait_type': 'Timestamp', 'value': str(dt.now())},
            {'trait_type': 'Certificate Type', 'value': 'Genesis'}
        ]
    
    operation_name = f'The Genesis NFT For {collection_name} ({collection_symbol}). NOTE: This NFT do NOT serve as a certificate! The certificate NFT starts from NFT index number #1.'

    metadata = {
            'name': operation_name,
            'image': f'https://ipfs.io/ipfs/{image_hash}',
            'attributes': attributes
        }
    metadata_file = f'static/datas/tmp/{str(uuid.uuid4())}.json'
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f)
    metadata_hash = _pin_to_IPFS(metadata_file)
    certificateTokenURI = f'https://ipfs.io/ipfs/{metadata_hash}'

    member_account_str = '|'.join(member_account)
    cmd = ["brownie", "run", "scripts/collectible/deploy_collectible.py", "main", collection_name, collection_symbol, member_account_str, str(min_signature), certificateTokenURI, "--network", "rinkeby"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    output, error = process.communicate()
    print(output, error)
    return output
