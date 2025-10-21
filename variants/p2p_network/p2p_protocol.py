"""
P2P Protocol Definitions for Proof-of-Inference Network

Defines message types, serialization, and protocol constants.
"""

import json
from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional


# Protocol version
PROTOCOL_VERSION = "1.0.0"
PROTOCOL_ID = f"/infraxa/inference/{PROTOCOL_VERSION}"


class MessageType(Enum):
    """Message types in the P2P protocol."""
    INFERENCE_REQUEST = "INFERENCE_REQUEST"
    INFERENCE_RESPONSE = "INFERENCE_RESPONSE"
    AUDIT_CHALLENGE = "AUDIT_CHALLENGE"
    AUDIT_PROOF = "AUDIT_PROOF"
    PROVIDER_ANNOUNCE = "PROVIDER_ANNOUNCE"
    PROVIDER_QUERY = "PROVIDER_QUERY"
    PROVIDER_LIST = "PROVIDER_LIST"
    HEARTBEAT = "HEARTBEAT"
    ERROR = "ERROR"


class VerificationMode(Enum):
    """Verification modes supported."""
    MERKLE = "merkle"
    FRAUD_PROOF = "fraud_proof"
    ZK_SNARK = "zk_snark"
    NONE = "none"  # For testing only


@dataclass
class InferenceRequest:
    """Request for AI inference."""
    job_id: str
    model: str
    prompt: Dict[str, Any]
    determinism: Dict[str, Any]
    verification_mode: str = "merkle"
    nonce: Optional[str] = None
    
    def to_json(self) -> str:
        data = asdict(self)
        data['type'] = MessageType.INFERENCE_REQUEST.value
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, data: str):
        obj = json.loads(data)
        obj.pop('type', None)
        return cls(**obj)


@dataclass
class InferenceResponse:
    """Response with inference results and proof."""
    job_id: str
    output_tokens: List[int]
    output_hash: str
    transcript_root: str
    provider_model_hash: str
    signature: str
    proof_type: str
    proof_data: Optional[Dict[str, Any]] = None
    
    def to_json(self) -> str:
        data = asdict(self)
        data['type'] = MessageType.INFERENCE_RESPONSE.value
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, data: str):
        obj = json.loads(data)
        obj.pop('type', None)
        return cls(**obj)


@dataclass
class AuditChallenge:
    """Challenge for audit verification."""
    job_id: str
    challenge_steps: List[int]
    vrf_proof: str
    
    def to_json(self) -> str:
        data = asdict(self)
        data['type'] = MessageType.AUDIT_CHALLENGE.value
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, data: str):
        obj = json.loads(data)
        obj.pop('type', None)
        return cls(**obj)


@dataclass
class AuditProof:
    """Proof for audit challenge."""
    job_id: str
    proofs: List[Dict[str, Any]]
    
    def to_json(self) -> str:
        data = asdict(self)
        data['type'] = MessageType.AUDIT_PROOF.value
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, data: str):
        obj = json.loads(data)
        obj.pop('type', None)
        return cls(**obj)


@dataclass
class ProviderAnnounce:
    """Provider announces capabilities."""
    peer_id: str
    models: List[str]
    model_hashes: Dict[str, str]
    verification_modes: List[str]
    reputation: float = 0.0
    stake: float = 0.0
    
    def to_json(self) -> str:
        data = asdict(self)
        data['type'] = MessageType.PROVIDER_ANNOUNCE.value
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, data: str):
        obj = json.loads(data)
        obj.pop('type', None)
        return cls(**obj)


@dataclass
class ProviderQuery:
    """Query for providers with specific capabilities."""
    model: Optional[str] = None
    verification_mode: Optional[str] = None
    min_reputation: float = 0.0
    
    def to_json(self) -> str:
        data = asdict(self)
        data['type'] = MessageType.PROVIDER_QUERY.value
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, data: str):
        obj = json.loads(data)
        obj.pop('type', None)
        return cls(**obj)


@dataclass
class ProviderList:
    """List of providers matching query."""
    providers: List[Dict[str, Any]]
    
    def to_json(self) -> str:
        data = asdict(self)
        data['type'] = MessageType.PROVIDER_LIST.value
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, data: str):
        obj = json.loads(data)
        obj.pop('type', None)
        return cls(**obj)


@dataclass
class Heartbeat:
    """Periodic heartbeat to maintain connection."""
    peer_id: str
    timestamp: float
    active_jobs: int = 0
    
    def to_json(self) -> str:
        data = asdict(self)
        data['type'] = MessageType.HEARTBEAT.value
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, data: str):
        obj = json.loads(data)
        obj.pop('type', None)
        return cls(**obj)


@dataclass
class ErrorMessage:
    """Error response."""
    error_code: str
    error_message: str
    job_id: Optional[str] = None
    
    def to_json(self) -> str:
        data = asdict(self)
        data['type'] = MessageType.ERROR.value
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, data: str):
        obj = json.loads(data)
        obj.pop('type', None)
        return cls(**obj)


def parse_message(data: str) -> Any:
    """Parse incoming message and return appropriate object."""
    try:
        obj = json.loads(data)
        msg_type = obj.get('type')
        
        if msg_type == MessageType.INFERENCE_REQUEST.value:
            return InferenceRequest.from_json(data)
        elif msg_type == MessageType.INFERENCE_RESPONSE.value:
            return InferenceResponse.from_json(data)
        elif msg_type == MessageType.AUDIT_CHALLENGE.value:
            return AuditChallenge.from_json(data)
        elif msg_type == MessageType.AUDIT_PROOF.value:
            return AuditProof.from_json(data)
        elif msg_type == MessageType.PROVIDER_ANNOUNCE.value:
            return ProviderAnnounce.from_json(data)
        elif msg_type == MessageType.PROVIDER_QUERY.value:
            return ProviderQuery.from_json(data)
        elif msg_type == MessageType.PROVIDER_LIST.value:
            return ProviderList.from_json(data)
        elif msg_type == MessageType.HEARTBEAT.value:
            return Heartbeat.from_json(data)
        elif msg_type == MessageType.ERROR.value:
            return ErrorMessage.from_json(data)
        else:
            raise ValueError(f"Unknown message type: {msg_type}")
    except Exception as e:
        raise ValueError(f"Failed to parse message: {e}")


# Protocol constants
MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 10MB
CONNECTION_TIMEOUT = 30  # seconds
HEARTBEAT_INTERVAL = 10  # seconds
PROVIDER_TTL = 60  # seconds
