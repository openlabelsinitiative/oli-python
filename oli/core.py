from web3 import Web3
import eth_account
from eth_keys import keys
from requests import Response

from oli.attestation.utils_validator import UtilsValidator
from oli.attestation.utils_other import UtilsOther
from oli.attestation.onchain import OnchainAttestations
from oli.attestation.offchain import OffchainAttestations
from oli.data.api import API
from oli.data.utils import UtilsData
from oli.data.trust import UtilsTrust
from dataclasses import dataclass

@dataclass
class PostResponse:
    """Standardized response for all POST operations"""
    success: bool
    onchain: bool
    transaction_hash: str = None
    uid: str = None
    uids: list = None
    eas_schema_chain: str = None  # only for onchain operations
    eas_schema: str = None
    status: str = None
    accepted: int = None  # for bulk operations
    duplicates: int = None  # for bulk operations
    failed_validation: list = None  # for bulk operations
    error: str = None
    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}

class OLI:
    def __init__(self, private_key: str=None, chain: str='Base', api_key: str=None, custom_rpc_url: str=None) -> None:
        """
        Initialize the OLI API client.
        
        Args:
            private_key (str): The private key to sign attestations
            chain (string): The blockchain network to connect to (e.g., 'Base', 'Arbitrum')
            custom_rpc_url (str): Custom RPC URL to connect to Blockchain
        """
        print("Initializing OLI API client...")

        # Set network (EAS contracts need to be deployed on the target chain)
        if chain.lower() == 'base':
            self.rpc = "https://mainnet.base.org"
            self.rpc_chain_number = 8453
            self.eas_address = "0x4200000000000000000000000000000000000021"  # EAS contract address on mainnet
        else:
            raise ValueError(f"Unsupported chain: {chain}. Currently only 'Base' is supported.")
        
        # Use provided RPC endpoint if nothing else specified
        if custom_rpc_url is not None:
            self.rpc = custom_rpc_url

        # Initialize Web3 instance from RPC endpoint
        self.w3 = Web3(Web3.HTTPProvider(self.rpc))
        if not self.w3.is_connected():
            raise Exception("Failed to connect to the Ethereum node")

        # Set local account using private key
        if private_key is None:
            print("WARNING: Private key not provided. Please set 'private_key' variable when initializing OLI.")
            print("WARNING: OLI client in read mode only.")
        else:
            try:
                # Convert the hex private key to the proper key object
                if private_key.startswith('0x'):
                    private_key_bytes = private_key[2:]
                else:
                    private_key_bytes = private_key
                # Create account from private key
                private_key_obj = keys.PrivateKey(bytes.fromhex(private_key_bytes))
                self.account = eth_account.Account.from_key(private_key_obj)
                self.address = self.account.address
                self.source_address = self.address # for Label Trust
            except Exception as e:
                print(f"Error initializing account from private key: {e}")
                self.account = None
                self.address = None
                self.source_address = None # for Label Trust
        
        # Label Pool Schema for OLI Label Pool
        self.oli_label_pool_schema = '0xcff83309b59685fdae9dad7c63d969150676d51d8eeda66799d1c4898b84556a' # v2.0.0 of EAS schema
        
        # Label Trust Schema for OLI Label Trust
        self.oli_label_trust_schema = '0x6d780a85bfad501090cd82868a0c773c09beafda609d54888a65c106898c363d'

        # Load EAS ABI & contract
        self.eas_abi = '[{"inputs": [],"stateMutability": "nonpayable","type": "constructor"},{"inputs": [],"name": "AccessDenied","type": "error"},{"inputs": [],"name": "AlreadyRevoked","type": "error"},{"inputs": [],"name": "AlreadyRevokedOffchain","type": "error"},{"inputs": [],"name": "AlreadyTimestamped","type": "error"},{"inputs": [],"name": "DeadlineExpired","type": "error"},{"inputs": [],"name": "InsufficientValue","type": "error"},{"inputs": [],"name": "InvalidAttestation","type": "error"},{"inputs": [],"name": "InvalidAttestations","type": "error"},{"inputs": [],"name": "InvalidExpirationTime","type": "error"},{"inputs": [],"name": "InvalidLength","type": "error"},{"inputs": [],"name": "InvalidNonce","type": "error"},{"inputs": [],"name": "InvalidOffset","type": "error"},{"inputs": [],"name": "InvalidRegistry","type": "error"},{"inputs": [],"name": "InvalidRevocation","type": "error"},{"inputs": [],"name": "InvalidRevocations","type": "error"},{"inputs": [],"name": "InvalidSchema","type": "error"},{"inputs": [],"name": "InvalidSignature","type": "error"},{"inputs": [],"name": "InvalidVerifier","type": "error"},{"inputs": [],"name": "Irrevocable","type": "error"},{"inputs": [],"name": "NotFound","type": "error"},{"inputs": [],"name": "NotPayable","type": "error"},{"inputs": [],"name": "WrongSchema","type": "error"},{"anonymous": false,"inputs": [{"indexed": true,"internalType": "address","name": "recipient","type": "address"},{"indexed": true,"internalType": "address","name": "attester","type": "address"},{"indexed": false,"internalType": "bytes32","name": "uid","type": "bytes32"},{"indexed": true,"internalType": "bytes32","name": "schemaUID","type": "bytes32"}],"name": "Attested","type": "event"},{"anonymous": false,"inputs": [{"indexed": false,"internalType": "uint256","name": "oldNonce","type": "uint256"},{"indexed": false,"internalType": "uint256","name": "newNonce","type": "uint256"}],"name": "NonceIncreased","type": "event"},{"anonymous": false,"inputs": [{"indexed": true,"internalType": "address","name": "recipient","type": "address"},{"indexed": true,"internalType": "address","name": "attester","type": "address"},{"indexed": false,"internalType": "bytes32","name": "uid","type": "bytes32"},{"indexed": true,"internalType": "bytes32","name": "schemaUID","type": "bytes32"}],"name": "Revoked","type": "event"},{"anonymous": false,"inputs": [{"indexed": true,"internalType": "address","name": "revoker","type": "address"},{"indexed": true,"internalType": "bytes32","name": "data","type": "bytes32"},{"indexed": true,"internalType": "uint64","name": "timestamp","type": "uint64"}],"name": "RevokedOffchain","type": "event"},{"anonymous": false,"inputs": [{"indexed": true,"internalType": "bytes32","name": "data","type": "bytes32"},{"indexed": true,"internalType": "uint64","name": "timestamp","type": "uint64"}],"name": "Timestamped","type": "event"},{"inputs": [{"components": [{"internalType": "bytes32","name": "schema","type": "bytes32"},{"components": [{"internalType": "address","name": "recipient","type": "address"},{"internalType": "uint64","name": "expirationTime","type": "uint64"},{"internalType": "bool","name": "revocable","type": "bool"},{"internalType": "bytes32","name": "refUID","type": "bytes32"},{"internalType": "bytes","name": "data","type": "bytes"},{"internalType": "uint256","name": "value","type": "uint256"}],"internalType": "struct AttestationRequestData","name": "data","type": "tuple"}],"internalType": "struct AttestationRequest","name": "request","type": "tuple"}],"name": "attest","outputs": [{"internalType": "bytes32","name": "","type": "bytes32"}],"stateMutability": "payable","type": "function"},{"inputs": [{"components": [{"internalType": "bytes32","name": "schema","type": "bytes32"},{"components": [{"internalType": "address","name": "recipient","type": "address"},{"internalType": "uint64","name": "expirationTime","type": "uint64"},{"internalType": "bool","name": "revocable","type": "bool"},{"internalType": "bytes32","name": "refUID","type": "bytes32"},{"internalType": "bytes","name": "data","type": "bytes"},{"internalType": "uint256","name": "value","type": "uint256"}],"internalType": "struct AttestationRequestData","name": "data","type": "tuple"},{"components": [{"internalType": "uint8","name": "v","type": "uint8"},{"internalType": "bytes32","name": "r","type": "bytes32"},{"internalType": "bytes32","name": "s","type": "bytes32"}],"internalType": "struct Signature","name": "signature","type": "tuple"},{"internalType": "address","name": "attester","type": "address"},{"internalType": "uint64","name": "deadline","type": "uint64"}],"internalType": "struct DelegatedAttestationRequest","name": "delegatedRequest","type": "tuple"}],"name": "attestByDelegation","outputs": [{"internalType": "bytes32","name": "","type": "bytes32"}],"stateMutability": "payable","type": "function"},{"inputs": [],"name": "getAttestTypeHash","outputs": [{"internalType": "bytes32","name": "","type": "bytes32"}],"stateMutability": "pure","type": "function"},{"inputs": [{"internalType": "bytes32","name": "uid","type": "bytes32"}],"name": "getAttestation","outputs": [{"components": [{"internalType": "bytes32","name": "uid","type": "bytes32"},{"internalType": "bytes32","name": "schema","type": "bytes32"},{"internalType": "uint64","name": "time","type": "uint64"},{"internalType": "uint64","name": "expirationTime","type": "uint64"},{"internalType": "uint64","name": "revocationTime","type": "uint64"},{"internalType": "bytes32","name": "refUID","type": "bytes32"},{"internalType": "address","name": "recipient","type": "address"},{"internalType": "address","name": "attester","type": "address"},{"internalType": "bool","name": "revocable","type": "bool"},{"internalType": "bytes","name": "data","type": "bytes"}],"internalType": "struct Attestation","name": "","type": "tuple"}],"stateMutability": "view","type": "function"},{"inputs": [],"name": "getDomainSeparator","outputs": [{"internalType": "bytes32","name": "","type": "bytes32"}],"stateMutability": "view","type": "function"},{"inputs": [],"name": "getName","outputs": [{"internalType": "string","name": "","type": "string"}],"stateMutability": "view","type": "function"},{"inputs": [{"internalType": "address","name": "account","type": "address"}],"name": "getNonce","outputs": [{"internalType": "uint256","name": "","type": "uint256"}],"stateMutability": "view","type": "function"},{"inputs": [{"internalType": "address","name": "revoker","type": "address"},{"internalType": "bytes32","name": "data","type": "bytes32"}],"name": "getRevokeOffchain","outputs": [{"internalType": "uint64","name": "","type": "uint64"}],"stateMutability": "view","type": "function"},{"inputs": [],"name": "getRevokeTypeHash","outputs": [{"internalType": "bytes32","name": "","type": "bytes32"}],"stateMutability": "pure","type": "function"},{"inputs": [],"name": "getSchemaRegistry","outputs": [{"internalType": "contract ISchemaRegistry","name": "","type": "address"}],"stateMutability": "pure","type": "function"},{"inputs": [{"internalType": "bytes32","name": "data","type": "bytes32"}],"name": "getTimestamp","outputs": [{"internalType": "uint64","name": "","type": "uint64"}],"stateMutability": "view","type": "function"},{"inputs": [{"internalType": "uint256","name": "newNonce","type": "uint256"}],"name": "increaseNonce","outputs": [],"stateMutability": "nonpayable","type": "function"},{"inputs": [{"internalType": "bytes32","name": "uid","type": "bytes32"}],"name": "isAttestationValid","outputs": [{"internalType": "bool","name": "","type": "bool"}],"stateMutability": "view","type": "function"},{"inputs": [{"components": [{"internalType": "bytes32","name": "schema","type": "bytes32"},{"components": [{"internalType": "address","name": "recipient","type": "address"},{"internalType": "uint64","name": "expirationTime","type": "uint64"},{"internalType": "bool","name": "revocable","type": "bool"},{"internalType": "bytes32","name": "refUID","type": "bytes32"},{"internalType": "bytes","name": "data","type": "bytes"},{"internalType": "uint256","name": "value","type": "uint256"}],"internalType": "struct AttestationRequestData[]","name": "data","type": "tuple[]"}],"internalType": "struct MultiAttestationRequest[]","name": "multiRequests","type": "tuple[]"}],"name": "multiAttest","outputs": [{"internalType": "bytes32[]","name": "","type": "bytes32[]"}],"stateMutability": "payable","type": "function"},{"inputs": [{"components": [{"internalType": "bytes32","name": "schema","type": "bytes32"},{"components": [{"internalType": "address","name": "recipient","type": "address"},{"internalType": "uint64","name": "expirationTime","type": "uint64"},{"internalType": "bool","name": "revocable","type": "bool"},{"internalType": "bytes32","name": "refUID","type": "bytes32"},{"internalType": "bytes","name": "data","type": "bytes"},{"internalType": "uint256","name": "value","type": "uint256"}],"internalType": "struct AttestationRequestData[]","name": "data","type": "tuple[]"},{"components": [{"internalType": "uint8","name": "v","type": "uint8"},{"internalType": "bytes32","name": "r","type": "bytes32"},{"internalType": "bytes32","name": "s","type": "bytes32"}],"internalType": "struct Signature[]","name": "signatures","type": "tuple[]"},{"internalType": "address","name": "attester","type": "address"},{"internalType": "uint64","name": "deadline","type": "uint64"}],"internalType": "struct MultiDelegatedAttestationRequest[]","name": "multiDelegatedRequests","type": "tuple[]"}],"name": "multiAttestByDelegation","outputs": [{"internalType": "bytes32[]","name": "","type": "bytes32[]"}],"stateMutability": "payable","type": "function"},{"inputs": [{"components": [{"internalType": "bytes32","name": "schema","type": "bytes32"},{"components": [{"internalType": "bytes32","name": "uid","type": "bytes32"},{"internalType": "uint256","name": "value","type": "uint256"}],"internalType": "struct RevocationRequestData[]","name": "data","type": "tuple[]"}],"internalType": "struct MultiRevocationRequest[]","name": "multiRequests","type": "tuple[]"}],"name": "multiRevoke","outputs": [],"stateMutability": "payable","type": "function"},{"inputs": [{"components": [{"internalType": "bytes32","name": "schema","type": "bytes32"},{"components": [{"internalType": "bytes32","name": "uid","type": "bytes32"},{"internalType": "uint256","name": "value","type": "uint256"}],"internalType": "struct RevocationRequestData[]","name": "data","type": "tuple[]"},{"components": [{"internalType": "uint8","name": "v","type": "uint8"},{"internalType": "bytes32","name": "r","type": "bytes32"},{"internalType": "bytes32","name": "s","type": "bytes32"}],"internalType": "struct Signature[]","name": "signatures","type": "tuple[]"},{"internalType": "address","name": "revoker","type": "address"},{"internalType": "uint64","name": "deadline","type": "uint64"}],"internalType": "struct MultiDelegatedRevocationRequest[]","name": "multiDelegatedRequests","type": "tuple[]"}],"name": "multiRevokeByDelegation","outputs": [],"stateMutability": "payable","type": "function"},{"inputs": [{"internalType": "bytes32[]","name": "data","type": "bytes32[]"}],"name": "multiRevokeOffchain","outputs": [{"internalType": "uint64","name": "","type": "uint64"}],"stateMutability": "nonpayable","type": "function"},{"inputs": [{"internalType": "bytes32[]","name": "data","type": "bytes32[]"}],"name": "multiTimestamp","outputs": [{"internalType": "uint64","name": "","type": "uint64"}],"stateMutability": "nonpayable","type": "function"},{"inputs": [{"components": [{"internalType": "bytes32","name": "schema","type": "bytes32"},{"components": [{"internalType": "bytes32","name": "uid","type": "bytes32"},{"internalType": "uint256","name": "value","type": "uint256"}],"internalType": "struct RevocationRequestData","name": "data","type": "tuple"}],"internalType": "struct RevocationRequest","name": "request","type": "tuple"}],"name": "revoke","outputs": [],"stateMutability": "payable","type": "function"},{"inputs": [{"components": [{"internalType": "bytes32","name": "schema","type": "bytes32"},{"components": [{"internalType": "bytes32","name": "uid","type": "bytes32"},{"internalType": "uint256","name": "value","type": "uint256"}],"internalType": "struct RevocationRequestData","name": "data","type": "tuple"},{"components": [{"internalType": "uint8","name": "v","type": "uint8"},{"internalType": "bytes32","name": "r","type": "bytes32"},{"internalType": "bytes32","name": "s","type": "bytes32"}],"internalType": "struct Signature","name": "signature","type": "tuple"},{"internalType": "address","name": "revoker","type": "address"},{"internalType": "uint64","name": "deadline","type": "uint64"}],"internalType": "struct DelegatedRevocationRequest","name": "delegatedRequest","type": "tuple"}],"name": "revokeByDelegation","outputs": [],"stateMutability": "payable","type": "function"},{"inputs": [{"internalType": "bytes32","name": "data","type": "bytes32"}],"name": "revokeOffchain","outputs": [{"internalType": "uint64","name": "","type": "uint64"}],"stateMutability": "nonpayable","type": "function"},{"inputs": [{"internalType": "bytes32","name": "data","type": "bytes32"}],"name": "timestamp","outputs": [{"internalType": "uint64","name": "","type": "uint64"}],"stateMutability": "nonpayable","type": "function"},{"inputs": [],"name": "version","outputs": [{"internalType": "string","name": "","type": "string"}],"stateMutability": "view","type": "function"}]'
        self.eas = self.w3.eth.contract(address=self.eas_address, abi=self.eas_abi)

        # Initialize OLI Label Schema
        self.api = API(self, api_key=api_key)
        self.tag_definitions = self.api.get_OLI_tags()
        try:
            self.tag_ids = list(self.tag_definitions.keys())
            self.tag_value_sets = self.api.get_OLI_value_sets()
        except Exception as e:
            self.tag_ids = []
            self.tag_value_sets = {}

        # Initialize OLI Label Pool
        self.onchain = OnchainAttestations(self, private_key)
        self.offchain = OffchainAttestations(self, private_key)
        self.utils_other = UtilsOther(self)
        self.validator = UtilsValidator(self)

        # Initialize OLI Label Trust
        self.utils_data = UtilsData(self)
        self.trust = UtilsTrust(self)

        print("...OLI client successfully initialized.")


    # OLI Label Pool post functions

    def submit_label(self, address: str, chain_id: str, tags: dict, onchain: bool=False, ref_uid: str="0x0000000000000000000000000000000000000000000000000000000000000000", gas_limit: int=-1, retry: int=4) -> PostResponse:
        try:
            if onchain:
                txn_hash, uid = self.onchain.submit_onchain_label(address, chain_id, tags, ref_uid, gas_limit)
                return PostResponse(
                    success=True,
                    onchain=True,
                    transaction_hash=txn_hash,
                    uid=uid,
                    eas_schema_chain=self.rpc_chain_number,
                    eas_schema=self.oli_label_pool_schema
                ).to_dict()
            else:
                response, uid = self.offchain.submit_offchain_label(address, chain_id, tags, ref_uid, retry)
                data = response.json()
                return PostResponse(
                    success=True,
                    onchain=False,
                    uid=uid if isinstance(uid, str) else uid[0] if uid else None,
                    eas_schema=self.oli_label_pool_schema,
                    status=data.get('status')
                ).to_dict()
        except Exception as e:
            return PostResponse(
                success=False,
                onchain=onchain,
                error=str(e)
            ).to_dict()

    def submit_label_bulk(self, labels: list, onchain: bool=False, gas_limit: int=-1, retry: int=4) -> PostResponse:
        try:
            if onchain:
                txn_hash, uids = self.onchain.submit_multi_onchain_labels(labels, gas_limit)
                return PostResponse(
                    success=True,
                    onchain=True,
                    transaction_hash=txn_hash,
                    uids=uids if isinstance(uids, list) else [uids],
                    eas_schema_chain=self.rpc_chain_number,
                    eas_schema=self.oli_label_pool_schema
                ).to_dict()
            else:
                response, uids = self.offchain.submit_offchain_labels_bulk(labels, retry)
                data = response.json()
                return PostResponse(
                    success=True,
                    onchain=False,
                    uids=uids if uids else None,
                    eas_schema=self.oli_label_pool_schema,
                    status=data.get('status'),
                    accepted=data.get('accepted'),
                    duplicates=data.get('duplicates'),
                    failed_validation=data.get('failed_validation')
                ).to_dict()
        except Exception as e:
            return PostResponse(
                success=False,
                onchain=onchain,
                error=str(e)
            ).to_dict()

    def submit_trust_list(self, owner_name: str, attesters: list=[], attestations: list=[], onchain: bool=False, gas_limit: int=-1, retry: int=4) -> PostResponse:
        try:
            if onchain:
                txn_hash, uid = self.onchain.submit_onchain_trust_list(owner_name, attesters, attestations, gas_limit)
                return PostResponse(
                    success=True,
                    onchain=True,
                    transaction_hash=txn_hash,
                    uid=uid,
                    eas_schema_chain=self.rpc_chain_number,
                    eas_schema=self.oli_label_trust_schema
                ).to_dict()
            else:
                response, uid = self.offchain.submit_offchain_trust_list(owner_name, attesters, attestations, retry)
                data = response.json()
                return PostResponse(
                    success=True,
                    onchain=False,
                    uid=uid if isinstance(uid, str) else uid[0] if uid else None,
                    eas_schema=self.oli_label_trust_schema,
                    status=data.get('status')
                ).to_dict()
        except Exception as e:
            return PostResponse(
                success=False,
                onchain=onchain,
                error=str(e)
            ).to_dict()
    
    def revoke_by_uid(self, uid: str, onchain: bool=False, gas_limit: int=200000) -> dict:
        # please note onchain revocations require ETH for gas fees
        try:
            # revoke based on onchain parameter
            if onchain:
                txn_hash = self.onchain.revoke_attestation(uid, gas_limit)
            else:
                txn_hash = self.offchain.revoke_attestation(uid, gas_limit)
            
            return PostResponse(
                success=True,
                onchain=True,
                transaction_hash=txn_hash,
                uid=uid,
                eas_schema_chain=self.rpc_chain_number
            ).to_dict()
            
        except Exception as e:
            return PostResponse(
                success=False,
                onchain=True,
                uid=uid,
                eas_schema_chain=self.rpc_chain_number,
                error=str(e)
            ).to_dict()

    def revoke_bulk_by_uids(self, uids: list, onchain: bool=False, gas_limit: int=10000000) -> dict:
        # please note onchain revocations require ETH for gas fees, furthermore it is recommended to keep the max number of uids to 100
        try:
            # revoke based on onchain parameter
            if onchain:
                txn_hash = self.onchain.multi_revoke_attestations(uids, gas_limit)
            else:
                txn_hash = self.offchain.multi_revoke_attestations(uids, gas_limit)
            
            return PostResponse(
                success=True,
                onchain=True,
                transaction_hash=txn_hash,
                uids=uids,
                eas_schema_chain=self.rpc_chain_number
            ).to_dict()
            
        except Exception as e:
            return PostResponse(
                success=False,
                onchain=True,
                uids=uids,
                eas_schema_chain=self.rpc_chain_number,
                error=str(e)
            ).to_dict()


    # OLI Label Pool validation functions

    def validate_label(self, address: str, chain_id: str, tags: dict, ref_uid: str="0x0000000000000000000000000000000000000000000000000000000000000000", auto_fix: bool=True) -> bool:
        return self.validator.validate_label_correctness(address, chain_id, tags, ref_uid, auto_fix)

    def validate_trust_list(self, owner_name: str, attesters: list=[], attestations: list=[]) -> bool:
        return self.validator.validate_trust_list_correctness(owner_name, attesters, attestations)


    # OLI Label Pool parquet exports

    def get_full_raw_export_parquet(self, file_path: str="raw_labels.parquet") -> str:
        return self.api.get_full_raw_export_parquet(file_path)
    
    def get_full_decoded_export_parquet(self, file_path: str="decoded_labels.parquet") -> str:
        return self.api.get_full_decoded_export_parquet(file_path)


    # OLI Label Trust functions

    def set_trust_node(self, address: str) -> None:
        if self.validator.validate_address(address):
            # set the source address for trust calculations
            self.source_address = address
            # compute the trust table for the new source address
            self.trust.trust_table = self.trust.compute_trust_table(self.trust.TrustGraph, source_node=address)
            return self.trust.trust_table

    def add_trust_list(self, owner_name: str='private_node', attesters: list=[], attestations: list=[], attester_address: str='0x0000000000000000000000000000000000000000') -> None:
        # if no trust node set, default to attester_address
        if not hasattr(self, 'source_address') or self.source_address is None:
            self.source_address = attester_address

        # add the trust list to the trust graph
        success = self.trust.add_trust_list(owner_name, attesters, attestations, attester_address)
        if success:
            # recompute the trust table for the current saved 'source_address'
            self.trust.trust_table = self.trust.compute_trust_table(self.trust.TrustGraph, source_node=self.source_address)
            return True


    # OLI Label Pool API functions (no api key required)

    def get_attestations(self, uid: str = None, attester: str = None, recipient: str = None, schema_info: str = None, since: str = None, order: str = "desc", limit: int = 1000) -> dict:
        return self.api.get_attestations(uid, attester, recipient, schema_info, since, order, limit)

    def get_trust_lists(self, uid: str = None, attester: str = None, order: str = "desc", limit: int = 100) -> dict:
        return self.api.get_trust_lists(uid, attester, order, limit)


    # OLI Label Pool API functions (api key required)

    def get_labels(self, address: str, chain_id: str=None, limit: int=1000, include_all: bool=False) -> dict:
        return self.api.get_labels(address, chain_id, limit, include_all)
    
    def get_trusted_labels(self, address: str, chain_id: str=None, limit: int=1000, include_all: bool=False, min_confidence: float=-1) -> dict:
        response = self.api.get_labels(address, chain_id, limit, include_all)
        filtered_labels = []
        for label in response['labels']:
            label['confidence'] = self.utils_data.get_confidence(label['attester'], label['tag_id'], label['chain_id'])
            if label['confidence'] >= min_confidence or min_confidence == -1:
                filtered_labels.append(label)
        response['labels'] = filtered_labels
        response['count_trusted'] = len(filtered_labels)
        return response
    
    def get_labels_bulk(self, addresses: list, chain_id: str = None, limit_per_address: int = 1000, include_all: bool = False) -> dict:
        return self.api.get_labels_bulk(addresses, chain_id, limit_per_address, include_all)
    
    def get_trusted_labels_bulk(self, addresses: list, chain_id: str = None, limit_per_address: int = 1000, include_all: bool = False, min_confidence: float = -1) -> dict:
        response = self.api.get_labels_bulk(addresses, chain_id, limit_per_address, include_all)
        for i, address in enumerate(response['results']):
            filtered_labels = []
            labels = address['labels']
            for label in labels:
                label['confidence'] = self.utils_data.get_confidence(label['attester'], label['tag_id'], label['chain_id'])
                if label['confidence'] >= min_confidence or min_confidence == -1:
                    filtered_labels.append(label)
            response['results'][i] = {'address': address['address'], 'labels': filtered_labels}
            response['results'][i]['count'] = len(labels)
            response['results'][i]['count_trusted'] = len(filtered_labels)
        return response

    def search_addresses_by_tag(self, tag_id: str, tag_value: str, chain_id: str = None, limit: int = 1000) -> dict:
        return self.api.search_addresses_by_tag(tag_id, tag_value, chain_id, limit)

    def search_trusted_addresses_by_tag(self, tag_id: str, tag_value: str, chain_id: str = None, limit: int = 1000, min_confidence: float = -1) -> dict:
        response = self.api.search_addresses_by_tag(tag_id, tag_value, chain_id, limit)
        filtered_addresses = []
        for label in response['results']:
            label['confidence'] = self.utils_data.get_confidence(label['attester'], tag_id, label['chain_id'])
            if label['confidence'] >= min_confidence or min_confidence == -1:
                filtered_addresses.append(label)
        response['results'] = filtered_addresses
        response['count_trusted'] = len(filtered_addresses)
        return response

    def get_attester_analytics(self, chain_id: str = None, limit: int = 100) -> dict:
        return self.api.get_attester_analytics(chain_id, limit)
