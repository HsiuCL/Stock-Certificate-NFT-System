from brownie import Collectible, accounts, network, config

def main(collection_name, collection_symbol, member_account_str, member_vote_str, min_signature, certificateTokenURI):
    member_account = member_account_str.split('|')
    member_vote = member_vote_str.split('|')
    min_signature = int(min_signature)
    dev = accounts.add(config['wallets']['from_key'])
    publish_source = False
    collectible = Collectible.deploy(collection_name, collection_symbol, member_account, member_vote, min_signature, certificateTokenURI, {"from": dev}, publish_source=publish_source)
    return collectible
