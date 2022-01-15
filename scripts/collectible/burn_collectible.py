from brownie import Collectible, accounts, config

def main(collectible_id):
    dev = accounts.add(config['wallets']['from_key'])
    collectible = Collectible[len(Collectible) - 1]
    result = collectible.burnCollectible(collectible_id, {'from': dev})
    print(result)
