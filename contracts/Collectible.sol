pragma solidity 0.6.6;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";

contract Collectible is ERC721{

  // uint256 public fee;
  uint256 public tokenCounter;
  address nftReceiver;
  string certificateTokenURI;

  constructor(string memory collection_name, string memory collection_symbol) public
  ERC721(collection_name, collection_symbol)
  {
    // fee = 0.1 * 10 ** 18;
    tokenCounter = 0;
  }

  function createCollectible(address receiver, string memory _certificateTokenURI)
  public returns (bytes32) {
    // certificateOwner = msg.sender;
    nftReceiver = receiver;
    certificateTokenURI = _certificateTokenURI;
    mintCollectible();
  }

  function mintCollectible() internal {
    uint256 newItemId = tokenCounter;
    // _safeMint(certificateOwner, newItemId);
    _safeMint(nftReceiver, newItemId);
    _setTokenURI(newItemId, certificateTokenURI);
    tokenCounter = tokenCounter + 1;
  }

  function setTokenURI(uint256 tokenId, string memory _tokenURI) public {
    require(
      _isApprovedOrOwner(_msgSender(), tokenId),
      "ERC721: transfer caller is not owner nor approved"
    );
    _setTokenURI(tokenId, _tokenURI);
  }

  function burnCollectible(uint256 tokenId) public {
    require(
      _isApprovedOrOwner(_msgSender(), tokenId),
      "ERC721: burn caller is not owner nor approved"
    );
    _burn(tokenId);
  }
}
