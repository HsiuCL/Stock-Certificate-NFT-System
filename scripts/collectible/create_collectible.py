from brownie import Collectible, accounts, config
import os
import json
import uuid

def main(nft_type, operation_name, description, image_path, attributes_string, receiver):
    image_hash = pin_to_IPFS(image_path)
    if len(image_hash) != 47:
        print('Error occured when pinning image to ipfs.')
        print(image_hash)
        return
    image_hash = image_hash[:-1]

    attributes_string = attributes_string.split('|')
    if nft_type == 'genesis':
        certificate_type = 'Genesis'
    else:
        certificate_type = 'Issue'
    attributes = [
            {'trait_type': 'Company Name', 'value': attributes_string[0]},
            {'trait_type': 'Company Symbol', 'value': attributes_string[1]},
            {'trait_type': 'Timestamp', 'value': attributes_string[2]},
            {'trait_type': 'Number Of Shares', 'value': attributes_string[3]},
            {'trait_type': 'Certificate Type', 'value': certificate_type}
        ]

    metadata = {
            'name': operation_name,
            'description': description,
            'image': f'https://ipfs.io/ipfs/{image_hash}',
            'attributes': attributes
        }
    metadata_file = f'metadata/rinkeby/{uuid.uuid4()}.json'
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f)
    metadata_hash = pin_to_IPFS(metadata_file)
    if len(metadata_hash) != 47:
        print('Error occured when pinning metadata to ipfs.')
        print(metadata_hash)
        return
    metadata_hash = metadata_hash[:-1]
    
    dev = accounts.add(config['wallets']['from_key'])
    collectible = Collectible[len(Collectible) - 1]
    result = collectible.createCollectible(receiver, f'https://ipfs.io/ipfs/{metadata_hash}', {'from': dev})
    print(f'https://ipfs.io/ipfs/{metadata_hash}')
    print(result)


def pin_to_IPFS(filename):
    ipfs_handler_path = './scripts/IPFS/ipfs_handler.js'
    cmd = os.popen(f'node -e \'require("{ipfs_handler_path}").ipfs_pin_file("{filename}")\'')
    result = cmd.read()
    cmd.close()
    return result
