"""
Cryptographic utilities for Proof-of-Inference system.
Provides hashing, Merkle trees, VRF, and signing primitives.
"""

import hashlib
import hmac
import json
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, asdict
import numpy as np


@dataclass
class MerkleProof:
    """Authentication path for a leaf in a Merkle tree."""
    leaf_index: int
    leaf_hash: str
    auth_path: List[Tuple[str, str]]  # [(hash, "left"|"right"), ...]
    root: str


class MerkleTree:
    """Simple Merkle tree implementation for transcript commitments."""
    
    def __init__(self, leaves: List[str]):
        """Build a Merkle tree from leaf hashes."""
        if not leaves:
            raise ValueError("Cannot build tree from empty leaves")
        
        self.leaves = leaves
        self.tree = self._build_tree(leaves)
        self.root = self.tree[-1][0] if self.tree else ""
    
    def _build_tree(self, leaves: List[str]) -> List[List[str]]:
        """Build the full tree bottom-up."""
        if not leaves:
            return []
        
        tree = [leaves[:]]
        current_level = leaves[:]
        
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                parent = self._hash_pair(left, right)
                next_level.append(parent)
            tree.append(next_level)
            current_level = next_level
        
        return tree
    
    @staticmethod
    def _hash_pair(left: str, right: str) -> str:
        """Hash two nodes together."""
        return hashlib.sha256(f"{left}|{right}".encode()).hexdigest()
    
    def get_proof(self, leaf_index: int) -> MerkleProof:
        """Generate authentication path for a specific leaf."""
        if leaf_index < 0 or leaf_index >= len(self.leaves):
            raise ValueError(f"Invalid leaf index: {leaf_index}")
        
        auth_path = []
        current_index = leaf_index
        
        for level in range(len(self.tree) - 1):
            level_size = self.tree[level]
            sibling_index = current_index ^ 1  # XOR with 1 flips last bit
            
            if sibling_index < len(level_size):
                sibling_hash = level_size[sibling_index]
                position = "right" if current_index % 2 == 0 else "left"
                auth_path.append((sibling_hash, position))
            
            current_index //= 2
        
        return MerkleProof(
            leaf_index=leaf_index,
            leaf_hash=self.leaves[leaf_index],
            auth_path=auth_path,
            root=self.root
        )
    
    @staticmethod
    def verify_proof(proof: MerkleProof) -> bool:
        """Verify a Merkle proof."""
        current_hash = proof.leaf_hash
        
        for sibling_hash, position in proof.auth_path:
            if position == "right":
                current_hash = MerkleTree._hash_pair(current_hash, sibling_hash)
            else:
                current_hash = MerkleTree._hash_pair(sibling_hash, current_hash)
        
        return current_hash == proof.root


def hash_data(data: Any) -> str:
    """Hash arbitrary data (converts to JSON first)."""
    if isinstance(data, (str, bytes)):
        content = data.encode() if isinstance(data, str) else data
    else:
        content = json.dumps(data, sort_keys=True).encode()
    return hashlib.sha256(content).hexdigest()


def quantize_logits(logits: np.ndarray, bits: int = 16) -> np.ndarray:
    """Quantize logits to reduce size and stabilize hashing."""
    if bits == 16:
        return logits.astype(np.float16)
    elif bits == 8:
        # Simple min-max quantization to int8
        min_val, max_val = logits.min(), logits.max()
        scale = (max_val - min_val) / 255.0
        quantized = ((logits - min_val) / scale).astype(np.uint8)
        return quantized
    else:
        raise ValueError(f"Unsupported quantization: {bits} bits")


def vrf_select_indices(seed: str, total_steps: int, k: int) -> List[int]:
    """
    Verifiable Random Function to select k audit indices from total_steps.
    Uses HMAC-based deterministic selection.
    """
    if k > total_steps:
        k = total_steps
    
    # Use HMAC as a VRF (simplified; real VRF would use EC crypto)
    indices = set()
    counter = 0
    
    while len(indices) < k:
        # Generate candidate index using HMAC
        key = seed.encode()
        message = f"{counter}".encode()
        hmac_digest = hmac.new(key, message, hashlib.sha256).digest()
        candidate = int.from_bytes(hmac_digest[:4], byteorder='big') % total_steps
        
        indices.add(candidate)
        counter += 1
    
    return sorted(list(indices))


def simple_sign(message: str, private_key: str) -> str:
    """Simple HMAC-based signing (replace with real crypto in production)."""
    key = private_key.encode()
    msg = message.encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def simple_verify(message: str, signature: str, public_key: str) -> bool:
    """Simple HMAC-based verification."""
    expected = simple_sign(message, public_key)  # Use public_key as key for demo
    return hmac.compare_digest(signature, expected)
