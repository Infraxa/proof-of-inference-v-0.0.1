"""
Optimistic Router for Fraud Proof System

Accepts responses immediately without verification.
Only verifies when challenged.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from dataclasses import dataclass
from typing import Dict, Optional
import time
from router import ProofOfInferenceRouter, AuditResult
from provider_sdk import JobResponse, AuditChallenge
from crypto_utils import simple_verify


@dataclass
class PendingResponse:
    """A response pending finalization."""
    response: JobResponse
    submitted_at: float
    challenge_deadline: float
    status: str  # 'pending', 'challenged', 'finalized', 'slashed'
    challenger: Optional[str] = None


class OptimisticRouter(ProofOfInferenceRouter):
    """Router that accepts responses optimistically."""
    
    def __init__(self, expected_model_hash: str, challenge_period: float = 24*3600):
        """
        Initialize optimistic router.
        
        Args:
            expected_model_hash: Expected model hash
            challenge_period: Challenge period in seconds (default 24 hours)
        """
        super().__init__(expected_model_hash, audit_rate=0.0)  # No automatic audits
        self.challenge_period = challenge_period
        self.pending_responses: Dict[str, PendingResponse] = {}
        self.finalized_responses: Dict[str, JobResponse] = {}
    
    def accept_response_optimistically(self, response: JobResponse, provider_public_key: str) -> bool:
        """
        Accept response immediately without verification.
        
        Args:
            response: Job response from provider
            provider_public_key: Provider's public key
            
        Returns:
            True (always accepts optimistically)
        """
        # Accept immediately (no verification - optimistic!)
        # Signature will be checked during challenge if needed
        current_time = time.time()
        self.pending_responses[response.job_id] = PendingResponse(
            response=response,
            submitted_at=current_time,
            challenge_deadline=current_time + self.challenge_period,
            status='pending'
        )
        
        print(f"✅ Response accepted optimistically (no verification)")
        print(f"   Challenge deadline: {self.challenge_period/3600:.1f} hours")
        
        return True
    
    def is_finalized(self, job_id: str) -> bool:
        """Check if response is finalized."""
        return job_id in self.finalized_responses
    
    def is_pending(self, job_id: str) -> bool:
        """Check if response is pending."""
        return job_id in self.pending_responses
    
    def can_finalize(self, job_id: str) -> bool:
        """Check if response can be finalized."""
        if job_id not in self.pending_responses:
            return False
        
        pending = self.pending_responses[job_id]
        return (
            pending.status == 'pending' and
            time.time() >= pending.challenge_deadline
        )
    
    def finalize_response(self, job_id: str) -> bool:
        """
        Finalize response after challenge period.
        
        Args:
            job_id: Job ID to finalize
            
        Returns:
            True if finalized successfully
        """
        if not self.can_finalize(job_id):
            print(f"❌ Cannot finalize {job_id}: Still in challenge period or already finalized")
            return False
        
        pending = self.pending_responses[job_id]
        self.finalized_responses[job_id] = pending.response
        del self.pending_responses[job_id]
        
        print(f"✅ Response finalized for job {job_id[:8]}")
        return True
    
    def submit_challenge(self, job_id: str, challenger_id: str, suspected_steps: list = None) -> bool:
        """
        Submit a challenge for a pending response.
        
        Args:
            job_id: Job ID to challenge
            challenger_id: Challenger identifier
            suspected_steps: Specific steps suspected of fraud (optional)
            
        Returns:
            True if challenge submitted successfully
        """
        if job_id not in self.pending_responses:
            print(f"❌ Cannot challenge {job_id}: Not found or already finalized")
            return False
        
        pending = self.pending_responses[job_id]
        
        if pending.status != 'pending':
            print(f"❌ Cannot challenge {job_id}: Already challenged or finalized")
            return False
        
        if time.time() > pending.challenge_deadline:
            print(f"❌ Cannot challenge {job_id}: Challenge period expired")
            return False
        
        # Mark as challenged
        pending.status = 'challenged'
        pending.challenger = challenger_id
        
        print(f"⚠️  Challenge submitted by {challenger_id[:8]}")
        print(f"   Job ID: {job_id[:8]}")
        print(f"   Provider must respond with audit proof")
        
        return True
    
    def resolve_challenge(self, job_id: str, audit_result: AuditResult) -> str:
        """
        Resolve a challenge with audit result.
        
        Args:
            job_id: Job ID
            audit_result: Result of audit verification
            
        Returns:
            'provider_honest' or 'fraud_detected'
        """
        if job_id not in self.pending_responses:
            print(f"❌ Cannot resolve challenge: Job {job_id} not found")
            return 'error'
        
        pending = self.pending_responses[job_id]
        
        if audit_result.passed:
            # Provider is honest
            pending.status = 'finalized'
            self.finalized_responses[job_id] = pending.response
            del self.pending_responses[job_id]
            
            print(f"✅ Challenge resolved: Provider is HONEST")
            print(f"   Challenger loses bond")
            return 'provider_honest'
        else:
            # Fraud detected!
            pending.status = 'slashed'
            
            print(f"🚨 Challenge resolved: FRAUD DETECTED")
            print(f"   Failed steps: {audit_result.failed_steps}")
            print(f"   Details: {audit_result.details}")
            print(f"   Provider will be slashed")
            print(f"   Challenger receives reward")
            return 'fraud_detected'
    
    def get_pending_count(self) -> int:
        """Get number of pending responses."""
        return len([p for p in self.pending_responses.values() if p.status == 'pending'])
    
    def get_challenged_count(self) -> int:
        """Get number of challenged responses."""
        return len([p for p in self.pending_responses.values() if p.status == 'challenged'])
    
    def get_stats(self) -> Dict:
        """Get router statistics."""
        return {
            'pending': self.get_pending_count(),
            'challenged': self.get_challenged_count(),
            'finalized': len(self.finalized_responses),
            'total': len(self.pending_responses) + len(self.finalized_responses)
        }
    
    def print_stats(self):
        """Print router statistics."""
        stats = self.get_stats()
        print("\n" + "="*50)
        print("📊 OPTIMISTIC ROUTER STATISTICS")
        print("="*50)
        print(f"Pending responses: {stats['pending']}")
        print(f"Challenged responses: {stats['challenged']}")
        print(f"Finalized responses: {stats['finalized']}")
        print(f"Total processed: {stats['total']}")
        print("="*50 + "\n")
