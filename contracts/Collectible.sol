pragma solidity 0.6.6;

import "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";

contract Collectible is ERC1155{

  mapping(address => uint8) private _is_board_member;
  address[] _board_member;
  mapping (uint256 => string) private _tokenURIs;
  uint constant VOTE_TOKEN = 0;
  uint256 public tokenCounter;
  uint256 public total_vote;
  uint MIN_SIGNATURE_RATE;
  uint private _proposalIdx;
  address private _system_addr;

  uint constant FOUNDING_PROPOSAL = 0;
  uint constant ISSUE_PROPOSAL = 1;
  uint constant BURN_PROPOSAL = 2;
  uint constant BURN_1_ISSUE_2_PROPOSAL = 3;
  uint constant GRANT_VOTE_PROPOSAL = 4;

  uint8 constant UNVOTED = 0;
  uint8 constant ACCEPT = 1;
  uint8 constant REJECT = 2;

  struct Proposal {
        address proposer;
        address address_1;
        address address_2;
        uint256 grant_vote_amount;
        uint256 token_id;
        uint proposal_type;
        uint256 accept_count;
        uint256 reject_count;
        string certificateTokenURI_1;
        string certificateTokenURI_2;
        uint256 min_accept;
        uint256 min_reject;
        mapping (address => uint8) signatures;
        mapping (address => uint256) vote;
    }

  mapping (uint => Proposal) private _proposals;
  uint[] _pending_proposals;

  modifier isBoardMember() {
    require(balanceOf(msg.sender, VOTE_TOKEN) > 0);
    _;
  }

  event FoundingProposalCreated(address proposer, uint proposalIdx, string certificateTokenURI);
  event IssueProposalCreated(address proposer, uint proposalIdx, address receiver, string certificateTokenURI);
  event BurnProposalCreated(address proposer, uint proposalIdx, uint256 tokenId);
  event BurnOneIssueTwoProposalCreated(address proposer, uint proposalIdx, uint256 tokenId, address receiver_1, string certificateTokenURI_1, address receiver_2, string certificateTokenURI_2);
  event GrantVoteProposalCreated(address proposer, uint proposalIdx, address receiver, uint256 amount);

  event FoundingProposalExecuted(address proposer, uint proposalIdx, string certificateTokenURI, uint256 newItemId);
  event IssueProposalExecuted(address proposer, uint proposalIdx, address receiver, string certificateTokenURI, uint256 newItemId);
  event BurnProposalExecuted(address proposer, uint proposalIdx, uint256 tokenId);
  event BurnOneIssueTwoProposalExecuted(address proposer, uint proposalIdx, uint256 tokenId, address receiver_1, string certificateTokenURI_1, address receiver_2, string certificateTokenURI_2, uint256 newItemId_1, uint256 newItemId_2);
  event GrantVoteProposalExecuted(address proposer, uint proposalIdx, address receiver, uint256 amount);

  event ProposalSigned(address signer, uint proposalIdx);
  event ProposalRejected(address rejecter, uint proposalIdx);
  event ProposalDeprecated(uint proposalIdx);

  event NewBoardMember(uint256 total_vote);
  event MinAcceptIs(uint256 min_accept);

  constructor(string memory collection_name, string memory collection_symbol, address[] memory member_address, uint256[] memory member_vote, uint min_signature_rate, string memory certificateTokenURI) public
  ERC1155(certificateTokenURI)
  {

    require(min_signature_rate > 1 && min_signature_rate <= 1000);
    require(member_address.length == member_vote.length);
    tokenCounter = 1;
    _system_addr = msg.sender;
    MIN_SIGNATURE_RATE = min_signature_rate;
    for (uint i = 0; i < member_vote.length; i++) {
      require(member_vote[i] >= 1);
      require(_is_board_member[member_address[i]] == 0);
      _is_board_member[member_address[i]] = 1;
      _board_member.push(member_address[i]);
      _mint(member_address[i], VOTE_TOKEN, member_vote[i], "");
    }
  }

  function uri(uint256 tokenId)
    override
    public
    view
    returns (string memory) {
      return(_tokenURIs[tokenId]);
  }

  function _setTokenURI(uint256 tokenId, string memory tokenURI)
    private {
     _tokenURIs[tokenId] = tokenURI;
  }

  function checkVote()
    public
    view
    returns (uint256, uint256){
    return (balanceOf(msg.sender, VOTE_TOKEN), total_vote);
  }

  function checkProposalVote(uint256 proposalIdx)
    public
    view
    returns (uint256, uint256, uint256, uint256) {
      Proposal storage proposal = _proposals[proposalIdx];
      return (proposal.accept_count, proposal.min_accept, proposal.reject_count, proposal.min_reject);
  }

  function _beforeTokenTransfer(address operator, address from, address to, uint256[] memory ids, uint256[] memory amounts, bytes memory data)
    internal
    virtual
    override {
    super._beforeTokenTransfer(operator, from, to, ids, amounts, data);

    if (from == address(0x0) && to != address(0x0)) {
      for (uint256 i = 0; i < ids.length; ++i) {
        if (ids[i] == VOTE_TOKEN) {
          total_vote += amounts[i];
          emit NewBoardMember(total_vote);
        }
      }
    }

    if (to == address(0x0) && from != address(0x0)) {
      for (uint256 i = 0; i < ids.length; ++i) {
        if (ids[i] == VOTE_TOKEN) {
          require(total_vote >= amounts[i]);
          total_vote -= amounts[i];
        }
      }
    }
  }

  function proposalVoteSetter(Proposal storage proposal)
    private {
      for (uint i = 0; i < _board_member.length; i++) {
        uint256 member_vote = balanceOf(_board_member[i], VOTE_TOKEN);
        if (member_vote > 0) {
          proposal.vote[_board_member[i]] = member_vote;
        } else {
          _is_board_member[_board_member[i]] = 0;
          _board_member[i] = _board_member[_board_member.length - 1];
          _board_member.pop();
          i--;
        }
      }
  }

  function foundingProposal(string memory certificateTokenURI)
    isBoardMember
    public {
    uint proposalIdx = _proposalIdx++;

    Proposal memory proposal;
    proposal.proposer = msg.sender;
    proposal.proposal_type = FOUNDING_PROPOSAL;
    proposal.accept_count = 0;
    proposal.reject_count= 0;
    proposal.certificateTokenURI_1 = certificateTokenURI;
    proposal.min_accept = (total_vote * MIN_SIGNATURE_RATE)/1000;
    proposal.min_reject = total_vote - proposal.min_accept;

    _proposals[proposalIdx] = proposal;
    proposalVoteSetter(_proposals[proposalIdx]);
    _pending_proposals.push(proposalIdx);
    emit FoundingProposalCreated(msg.sender, proposalIdx, certificateTokenURI);
    signProposal(proposalIdx);
  }

  function safeTransferFrom(address from, address to, uint256 id, uint256 amount, bytes memory data)
    override
    public {
      if (id == VOTE_TOKEN && amount > 0 && _is_board_member[to] == 0 && address(0x0) != to) {
        _board_member.push(to);
        _is_board_member[to] = 1;
      }
      super.safeTransferFrom(from, to, id, amount, data);
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
    proposal.accept_count = 0;
    proposal.reject_count= 0;
    proposal.min_accept = (total_vote * MIN_SIGNATURE_RATE)/1000;
    emit MinAcceptIs(proposal.min_accept);
    proposal.min_reject = total_vote - proposal.min_accept;

    _proposals[proposalIdx] = proposal;
    proposalVoteSetter(_proposals[proposalIdx]);
    _pending_proposals.push(proposalIdx);
    emit IssueProposalCreated(msg.sender, proposalIdx, receiver, certificateTokenURI);
    signProposal(proposalIdx);
  }

  function burnProposal(uint256 tokenId)
    isBoardMember
    public {
    require(tokenId != 0);
    uint proposalIdx = _proposalIdx++; 
    Proposal memory proposal;
    proposal.proposer = msg.sender;
    proposal.token_id = tokenId;
    proposal.proposal_type = BURN_PROPOSAL;
    proposal.accept_count = 0;
    proposal.reject_count= 0;
    proposal.min_accept = (total_vote * MIN_SIGNATURE_RATE)/1000;
    proposal.min_reject = total_vote - proposal.min_accept;

    _proposals[proposalIdx] = proposal;
    proposalVoteSetter(_proposals[proposalIdx]);
    _pending_proposals.push(proposalIdx);
    emit BurnProposalCreated(msg.sender, proposalIdx, tokenId);
    signProposal(proposalIdx);
  }

  function burnOneIssueTwoProposal(uint256 tokenId, address receiver_1, string memory certificateTokenURI_1, address receiver_2, string memory certificateTokenURI_2)
    isBoardMember
    public {
    require(tokenId != 0);
    uint proposalIdx = _proposalIdx++;
    Proposal memory proposal;
    proposal.proposer = msg.sender;
    proposal.token_id = tokenId;
    proposal.address_1 = receiver_1;
    proposal.certificateTokenURI_1 = certificateTokenURI_1;
    proposal.address_2 = receiver_2;
    proposal.certificateTokenURI_2 = certificateTokenURI_2;
    proposal.proposal_type = BURN_1_ISSUE_2_PROPOSAL;
    proposal.accept_count = 0;
    proposal.reject_count= 0;
    proposal.min_accept = (total_vote * MIN_SIGNATURE_RATE)/1000;
    proposal.min_reject = total_vote - proposal.min_accept;
    
    _proposals[proposalIdx] = proposal;
    proposalVoteSetter(_proposals[proposalIdx]);
    _pending_proposals.push(proposalIdx);
    emit BurnOneIssueTwoProposalCreated(msg.sender, proposalIdx, tokenId, receiver_1, certificateTokenURI_1, receiver_2, certificateTokenURI_2);
    signProposal(proposalIdx);
  }

  function grantVoteProposal(address receiver, uint256 amount)
    isBoardMember
    public {
    uint proposalIdx = _proposalIdx++;
    Proposal memory proposal;
    proposal.proposer = msg.sender;
    proposal.address_1 = receiver;
    proposal.grant_vote_amount = amount;
    proposal.proposal_type = GRANT_VOTE_PROPOSAL;
    proposal.min_accept = (total_vote * MIN_SIGNATURE_RATE)/1000;
    proposal.min_reject = total_vote - proposal.min_accept;

    _proposals[proposalIdx] = proposal;
    proposalVoteSetter(_proposals[proposalIdx]);
    _pending_proposals.push(proposalIdx);
    emit GrantVoteProposalCreated(msg.sender, proposalIdx, receiver, amount);
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
      return MIN_SIGNATURE_RATE;
  }

  function rejectProposal(uint proposalIdx)
    public {
    Proposal storage proposal = _proposals[proposalIdx];
    require(proposal.vote[msg.sender] > 0);
    require(address(0x0) != proposal.proposer);
    require(proposal.signatures[msg.sender] != REJECT);
    if (proposal.signatures[msg.sender] == ACCEPT) {
      proposal.accept_count -= proposal.vote[msg.sender];
    }
    proposal.signatures[msg.sender] = REJECT;
    proposal.reject_count += proposal.vote[msg.sender];
    emit ProposalRejected(msg.sender, proposalIdx);
    if (proposal.reject_count > proposal.min_reject) {
      deleteProposal(proposalIdx);
      emit ProposalDeprecated(proposalIdx);
    }
  }

  function signProposal(uint proposalIdx)
    public {
    Proposal storage proposal = _proposals[proposalIdx];
    require(proposal.vote[msg.sender] > 0);
    require(address(0x0) != proposal.proposer);
    require(proposal.signatures[msg.sender] != ACCEPT);
    if (proposal.signatures[msg.sender] == REJECT) {
      proposal.reject_count -= proposal.vote[msg.sender];
    }
    proposal.signatures[msg.sender] = ACCEPT;
    proposal.accept_count += proposal.vote[msg.sender];
    emit ProposalSigned(msg.sender, proposalIdx);
    if (proposal.accept_count >= proposal.min_accept) {
      if (proposal.proposal_type == FOUNDING_PROPOSAL) {
        uint256 newItemId = tokenCounter++;
        _mint(_system_addr, newItemId, 1, "");
        _setTokenURI(newItemId, proposal.certificateTokenURI_1);
        emit FoundingProposalExecuted(proposal.proposer, proposalIdx, proposal.certificateTokenURI_1, newItemId);
      } else if (proposal.proposal_type == ISSUE_PROPOSAL) {
        uint256 newItemId = tokenCounter++;
        _mint(proposal.address_1, newItemId, 1, "");
        _setTokenURI(newItemId, proposal.certificateTokenURI_1);
        emit IssueProposalExecuted(proposal.proposer, proposalIdx, proposal.address_1, proposal.certificateTokenURI_1, newItemId);
      } else if (proposal.proposal_type == BURN_1_ISSUE_2_PROPOSAL) {
        _burn(_system_addr, proposal.token_id, 1);
        uint256 newItemId = tokenCounter++;
        _mint(proposal.address_1, newItemId, 1, "");
        _setTokenURI(newItemId, proposal.certificateTokenURI_1);
        newItemId = tokenCounter++;
        _mint(proposal.address_2, newItemId, 1, "");
        _setTokenURI(newItemId, proposal.certificateTokenURI_2);
        emit BurnOneIssueTwoProposalExecuted(proposal.proposer, proposalIdx, proposal.token_id, proposal.address_1, proposal.certificateTokenURI_1, proposal.address_2, proposal.certificateTokenURI_2, newItemId-1, newItemId);
      } else if (proposal.proposal_type == BURN_PROPOSAL) {
        _burn(_system_addr, proposal.token_id, 1);
        emit BurnProposalExecuted(proposal.proposer, proposalIdx, proposal.token_id);
      } else if (proposal.proposal_type == GRANT_VOTE_PROPOSAL) {
        _mint(proposal.address_1, VOTE_TOKEN, proposal.grant_vote_amount, "");
        emit GrantVoteProposalExecuted(proposal.proposer, proposalIdx, proposal.address_1, proposal.grant_vote_amount);
      }
      deleteProposal(proposalIdx);
    }
  }

  function deleteProposal(uint proposalIdx)
    private {
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
