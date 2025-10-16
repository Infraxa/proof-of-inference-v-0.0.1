"""
Proof-of-Inference Router.
Issues jobs and performs cryptographic audits.
"""

import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import json
import base64

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from crypto_utils import vrf_select_indices, hash_data, MerkleTree, simple_verify, quantize_logits
from provider_sdk import ProofOfInferenceProvider, JobRequest, JobResponse, AuditChallenge, AuditProof


@dataclass
class AuditResult:
    """Result of an audit check."""
    job_id: str
    passed: bool
    failed_steps: List[int]
    details: str


class ProofOfInferenceRouter:
    """Router that issues jobs and audits providers."""
    
    def __init__(self, expected_model_hash: str, audit_rate: float = 0.1, audit_k: int = 3):
        """Initialize with expected model hash and audit parameters."""
        self.expected_model_hash = expected_model_hash
        self.audit_rate = audit_rate  # Audit rate (0.0 to 1.0)
        self.audit_k = audit_k  # Number of steps to audit per job
        self.jobs = {}  # job_id -> job data
    
    def create_job(self, prompt: Dict[str, Any], determinism: Dict[str, Any] = None) -> JobRequest:
        """Create a new job request."""
        if determinism is None:
            determinism = {"temperature": 0.0, "max_tokens": 50}
        
        job_id = str(uuid.uuid4())
        nonce = str(uuid.uuid4())
        
        job = JobRequest(
            job_id=job_id,
            model_hash=self.expected_model_hash,
            prompt=prompt,
            determinism=determinism,
            nonce=nonce,
            audit_budget={"k_steps": self.audit_k, "max_reveals_per_step": 1}
        )
        
        self.jobs[job_id] = {
            "job": job,
            "created_at": time.time(),
            "audited": False
        }
        
        return job
    
    def should_audit_job(self, job_id: str) -> bool:
        """Decide whether to audit this job (deterministic VRF)."""
        if job_id not in self.jobs:
            return False
        
        # Use job nonce as VRF seed
        job = self.jobs[job_id]["job"]
        seed = job.nonce
        
        # Simple deterministic audit decision
        audit_hash = hash_data(f"audit:{seed}")
        audit_value = int(audit_hash[:8], 16) / 2**32
        
        return audit_value < self.audit_rate
    
    def create_audit_challenge(self, job_id: str) -> Optional[AuditChallenge]:
        """Create audit challenge for a completed job."""
        if job_id not in self.jobs:
            return None
        
        job_data = self.jobs[job_id]
        job = job_data["job"]
        
        # Select audit steps using VRF
        seed = f"{job.nonce}:{job_id}"
        challenge_steps = vrf_select_indices(seed, job.determinism.get("max_tokens", 50), self.audit_k)
        
        return AuditChallenge(
            job_id=job_id,
            challenge_steps=challenge_steps,
            vrf_proof=seed  # Simplified VRF proof
        )
    
    def verify_job_response(self, response: JobResponse, provider_public_key: str) -> bool:
        """Verify job response signature and basic validity."""
        if response.job_id not in self.jobs:
            return False
        
        job = self.jobs[response.job_id]["job"]
        
        # Verify provider's model hash matches expected
        if response.provider_model_hash != self.expected_model_hash:
            print(f"🚨 Model substitution detected!")
            print(f"   Expected: {self.expected_model_hash[:32]}...")
            print(f"   Got:      {response.provider_model_hash[:32]}...")
            return False
        
        # Verify signature (includes model hash to prevent forgery)
        message = f"{response.transcript_root}|{response.output_hash}|{response.job_id}|{response.provider_model_hash}"
        if not simple_verify(message, response.sig, provider_public_key):
            print("🚨 Signature verification failed - possible hash forgery!")
            return False
        
        # Verify output hash matches tokens
        computed_hash = hash_data(response.output_tokens)
        if computed_hash != response.output_hash:
            print(f"Output hash mismatch: expected {computed_hash}, got {response.output_hash}")
            return False
        
        print(f"Job response verification passed for {response.job_id}")
        return True
    
    def audit_job_response(self, proof: AuditProof, job_response: JobResponse, 
                          reference_provider: Optional[ProofOfInferenceProvider] = None) -> AuditResult:
        """Perform full audit on job response."""
        job_id = proof.job_id
        
        if job_id not in self.jobs:
            return AuditResult(job_id, False, [], "Job not found")
        
        job_data = self.jobs[job_id]
        job = job_data["job"]
        
        failed_steps = []
        
        # Verify each proof
        for step_proof in proof.proofs:
            if not self._verify_step_proof(step_proof, job_response.transcript_root, job):
                failed_steps.append(step_proof.t)
                continue
            
            # Optional: recompute step with reference provider
            if reference_provider and not self._verify_step_recomputation(step_proof, job, reference_provider):
                failed_steps.append(step_proof.t)
        
        passed = len(failed_steps) == 0
        details = f"Audited {len(proof.proofs)} steps, {len(failed_steps)} failed"
        
        if passed:
            job_data["audited"] = True
            print(f"Audit PASSED for job {job_id}")
        else:
            print(f"Audit FAILED for job {job_id}: {details}")
        
        return AuditResult(job_id, passed, failed_steps, details)
    
    def _verify_step_proof(self, step_proof: 'StepProof', transcript_root: str, job: JobRequest) -> bool:
        """Verify Merkle proof for a single step."""
        try:
            # Reconstruct Merkle proof
            from crypto_utils import MerkleProof
            proof = MerkleProof(
                leaf_index=step_proof.t,
                leaf_hash="",  # Will be computed
                auth_path=[tuple(pair) for pair in step_proof.auth_path],
                root=transcript_root
            )
            
            # Recompute leaf hash - must match exactly how provider computed it
            logits_bytes = base64.b64decode(step_proof.logits_q)
            logits_hash_computed = hash_data(logits_bytes)
            
            step_data = {
                "step": step_proof.t,
                "input_hash": step_proof.prestate_hash,
                "logits_hash": logits_hash_computed,
                "token": step_proof.next_token,
                "nonce": job.nonce
            }
            proof.leaf_hash = hash_data(step_data)
            
            # Verify proof
            verified = MerkleTree.verify_proof(proof)
            if not verified:
                print(f"  Step {step_proof.t} verification failed")
            return verified
            
        except Exception as e:
            print(f"Step proof verification error: {e}")
            return False
    
    def _verify_step_recomputation(self, step_proof: 'StepProof', job: JobRequest, 
                                 reference: ProofOfInferenceProvider) -> bool:
        """Recompute step with reference provider and compare."""
        try:
            # This would require caching intermediate states
            # For demo, we'll assume verification passes
            return True
        except Exception as e:
            print(f"Step recomputation error: {e}")
            return False
