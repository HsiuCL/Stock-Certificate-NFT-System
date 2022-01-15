from brownie import Collectible, accounts, network, config

def main(collection_name, collection_symbol):
    dev = accounts.add(config['wallets']['from_key'])
    publish_source = False
    collectible = Collectible.deploy(collection_name, collection_symbol, {"from": dev}, publish_source=publish_source)
    return collectible
