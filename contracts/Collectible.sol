pragma solidity 0.6.6;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";

contract Collectible is ERC721{

  // uint256 public fee;
  uint256 public tokenCounter;
  mapping(address => uint8) private _board_member;
  uint MIN_SIGNATURE;
  uint TOTAL_BOARD_NUMBER;
  uint private _proposalIdx;
  address private _system_addr;

  uint constant FOUNDING_PROPOSAL = 0;
  uint constant ISSUE_PROPOSAL = 1;
  uint constant BURN_PROPOSAL = 2;
  uint constant BURN_1_ISSUE_2_PROPOSAL = 3;

  struct Proposal {
        address proposer;
        address address_1;
        address address_2;
        uint256 token_id;
        uint proposal_type;
        uint8 signature_count;
        uint8 reject_count;
        string certificateTokenURI_1;
        string certificateTokenURI_2;
        mapping (address => uint8) signatures;
    }

  mapping (uint => Proposal) private _proposals;
  uint[] _pending_proposals;

  modifier isBoardMember() {
    require(_board_member[msg.sender] == 1);
    _;
  }

  event FoundingProposalCreated(address proposer, uint proposalIdx, string certificateTokenURI);
  event IssueProposalCreated(address proposer, uint proposalIdx, address receiver, string certificateTokenURI);
  event BurnProposalCreated(address proposer, uint proposalIdx, uint256 tokenId);
  event BurnOneIssueTwoProposalCreated(address proposer, uint proposalIdx, uint256 tokenId, address receiver_1, string certificateTokenURI_1, address receiver_2, string certificateTokenURI_2);
  event ProposalSigned(address signer, uint proposalIdx);
  event ProposalRejected(address rejecter, uint proposalIdx);
  event ProposalExecuted(address proposer, uint proposalIdx);
  event ProposalDeprecated(uint proposalIdx);

  constructor(string memory collection_name, string memory collection_symbol, address[] memory member_address, uint min_signature, string memory certificateTokenURI) public
  ERC721(collection_name, collection_symbol)
  {
    tokenCounter = 0;
    _system_addr = msg.sender;
    MIN_SIGNATURE = min_signature;
    TOTAL_BOARD_NUMBER = member_address.length;
    for (uint i = 0; i < member_address.length; i++) {
      _board_member[member_address[i]] = 1;
    }
    uint256 newItemId = tokenCounter++;
    _safeMint(_system_addr, newItemId);
    _setTokenURI(newItemId, certificateTokenURI);
  }

  function foundingProposal(string memory certificateTokenURI)
    isBoardMember
    public {
    uint proposalIdx = _proposalIdx++;

    Proposal memory proposal;
    proposal.proposer = msg.sender;
    proposal.proposal_type = FOUNDING_PROPOSAL;
    proposal.signature_count = 0;
    proposal.reject_count= 0;
    proposal.certificateTokenURI_1 = certificateTokenURI;

    _proposals[proposalIdx] = proposal;
    _pending_proposals.push(proposalIdx);
    emit FoundingProposalCreated(msg.sender, proposalIdx, certificateTokenURI);
    signProposal(proposalIdx);
  }

  function issueProposal(address receiver, string memory certificateTokenURI)
    isBoardMember
    public {
    uint proposalIdx = _proposalIdx++;
    Proposal memory proposal;
    proposal.proposer = msg.sender;
    proposal.address_1 = receiver;
    proposal.proposal_type = ISSUE_PROPOSAL;
    proposal.certificateTokenURI_1 = certificateTokenURI;
    proposal.signature_count = 0;
    proposal.reject_count= 0;

    _proposals[proposalIdx] = proposal;
    _pending_proposals.push(proposalIdx);
    emit IssueProposalCreated(msg.sender, proposalIdx, receiver, certificateTokenURI);
    signProposal(proposalIdx);
  }

  function burnProposal(uint256 tokenId)
    isBoardMember
    public {
    uint proposalIdx = _proposalIdx++; 
    Proposal memory proposal;
    proposal.proposer = msg.sender;
    proposal.token_id = tokenId;
    proposal.proposal_type = BURN_PROPOSAL;
    proposal.signature_count = 0;
    proposal.reject_count= 0;

    _proposals[proposalIdx] = proposal;
    _pending_proposals.push(proposalIdx);
    emit BurnProposalCreated(msg.sender, proposalIdx, tokenId);
    signProposal(proposalIdx);
  }

  function burnOneIssueTwoProposal(uint256 tokenId, address receiver_1, string memory certificateTokenURI_1, address receiver_2, string memory certificateTokenURI_2)
    isBoardMember
    public {
    uint proposalIdx = _proposalIdx++;
    Proposal memory proposal;
    proposal.proposer = msg.sender;
    proposal.token_id = tokenId;
    proposal.address_1 = receiver_1;
    proposal.certificateTokenURI_1 = certificateTokenURI_1;
    proposal.address_2 = receiver_2;
    proposal.certificateTokenURI_2 = certificateTokenURI_2;
    proposal.proposal_type = BURN_1_ISSUE_2_PROPOSAL;
    proposal.signature_count = 0;
    proposal.reject_count= 0;
    
    _proposals[proposalIdx] = proposal;
    _pending_proposals.push(proposalIdx);
    emit BurnOneIssueTwoProposalCreated(msg.sender, proposalIdx, tokenId, receiver_1, certificateTokenURI_1, receiver_2, certificateTokenURI_2);
    signProposal(proposalIdx);
  }

  function getPendingProposals()
    public
    view
    returns (uint[] memory) {
    return _pending_proposals;
  }

  function getMinRequiredSignature()
    public
    view
    returns (uint) {
      return MIN_SIGNATURE;
  }

  function getTotalBoardMemberNumber()
    public
    view
    returns (uint) {
      return TOTAL_BOARD_NUMBER;
  }

  function rejectProposal(uint proposalIdx)
    isBoardMember
    public {
    Proposal storage proposal = _proposals[proposalIdx];
    require(address(0x0) != proposal.proposer);
    require(proposal.signatures[msg.sender] != 2);
    if (proposal.signatures[msg.sender] == 1) {
      proposal.signature_count--;
    }
    proposal.signatures[msg.sender] = 2;
    proposal.reject_count++;
    emit ProposalRejected(msg.sender, proposalIdx);
    if (proposal.reject_count > TOTAL_BOARD_NUMBER - MIN_SIGNATURE) {
      deleteProposal(proposalIdx);
      emit ProposalDeprecated(proposalIdx);
    }
  }

  function signProposal(uint proposalIdx)
    isBoardMember
    public {
    Proposal storage proposal = _proposals[proposalIdx];
    require(address(0x0) != proposal.proposer);
    require(proposal.signatures[msg.sender] != 1);
    if (proposal.signatures[msg.sender] == 2) {
      proposal.reject_count--;
    }
    proposal.signatures[msg.sender] = 1;
    proposal.signature_count++;
    emit ProposalSigned(msg.sender, proposalIdx);

    if (proposal.signature_count >= MIN_SIGNATURE) {
      if (proposal.proposal_type == FOUNDING_PROPOSAL) {
        uint256 newItemId = tokenCounter++;
        _safeMint(_system_addr, newItemId);
        _setTokenURI(newItemId, proposal.certificateTokenURI_1);

      } else if (proposal.proposal_type == ISSUE_PROPOSAL) {
        uint256 newItemId = tokenCounter++;
        _safeMint(proposal.address_1, newItemId);
        _setTokenURI(newItemId, proposal.certificateTokenURI_1);

      } else if (proposal.proposal_type == BURN_1_ISSUE_2_PROPOSAL) {
        _burn(proposal.token_id);
        uint256 newItemId = tokenCounter++;
        _safeMint(proposal.address_1, newItemId);
        _setTokenURI(newItemId, proposal.certificateTokenURI_1);
        newItemId = tokenCounter++;
        _safeMint(proposal.address_2, newItemId);
        _setTokenURI(newItemId, proposal.certificateTokenURI_2);

      } else if (proposal.proposal_type == BURN_PROPOSAL) {
        _burn(proposal.token_id);
      }
      emit ProposalExecuted(proposal.proposer, proposalIdx);
      deleteProposal(proposalIdx);
    }
  }

  function deleteProposal(uint proposalIdx)
    isBoardMember
    public {
      for (uint i = 0; i < _pending_proposals.length; i++) {
        if (_pending_proposals[i] == proposalIdx) {
          _pending_proposals[i] = _pending_proposals[_pending_proposals.length - 1];
          break;
        }
      }
      delete _pending_proposals[_pending_proposals.length - 1];
      delete _proposals[proposalIdx];
  }
}
