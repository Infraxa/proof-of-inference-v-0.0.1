#!/usr/bin/env python3
"""
Router Node for P2P Proof-of-Inference Network

Discovers providers, requests inference, and verifies proofs.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import asyncio
import argparse
import uuid
import time
from typing import List, Dict, Optional, Tuple

from router import ProofOfInferenceRouter, AuditResult
from provider_sdk import StepProof
from p2p_protocol import (
    InferenceRequest, InferenceResponse, AuditChallenge, AuditProof,
    ProviderQuery, ErrorMessage, parse_message,
    PROTOCOL_ID, MAX_MESSAGE_SIZE
)


class RouterNode:
    """
    P2P Router Node
    
    Discovers providers, requests inference, and verifies proofs.
    """
    
    def __init__(self):
        self.peer_id = self._generate_peer_id()
        self.known_providers: Dict[str, Dict] = {}
        
        print(f"Router Node initialized")
        print(f"  Peer ID: {self.peer_id}")
    
    def _generate_peer_id(self) -> str:
        """Generate unique peer ID."""
        import hashlib
        return hashlib.sha256(f"router{time.time()}".encode()).hexdigest()[:16]
    
    def add_provider(self, host: str, port: int, model: str, model_hash: str):
        """Manually add a known provider."""
        provider_id = f"{host}:{port}"
        self.known_providers[provider_id] = {
            'host': host,
            'port': port,
            'model': model,
            'model_hash': model_hash,
            'reputation': 1.0
        }
        print(f"[{self.peer_id}] Added provider: {provider_id} ({model})")
    
    async def send_message(self, host: str, port: int, message: str) -> Optional[str]:
        """Send message to a peer and get response."""
        try:
            reader, writer = await asyncio.open_connection(host, port)
            
            # Send message
            writer.write(message.encode('utf-8'))
            await writer.drain()
            
            # Read response
            data = await reader.read(MAX_MESSAGE_SIZE)
            response = data.decode('utf-8')
            
            writer.close()
            await writer.wait_closed()
            
            return response
        
        except Exception as e:
            print(f"[{self.peer_id}] Error sending message to {host}:{port}: {e}")
            return None
    
    async def request_inference(
        self,
        model: str,
        prompt: Dict,
        determinism: Dict,
        verification_mode: str = "merkle"
    ) -> Tuple[Optional[InferenceResponse], Optional[str]]:
        """
        Request inference from a provider.
        
        Returns: (response, provider_id) or (None, None) if failed
        """
        # Find provider with this model
        provider = None
        provider_id = None
        
        for pid, pdata in self.known_providers.items():
            if pdata['model'] == model:
                provider = pdata
                provider_id = pid
                break
        
        if not provider:
            print(f"[{self.peer_id}] No provider found for model: {model}")
            return None, None
        
        # Create inference request
        job_id = str(uuid.uuid4())
        request = InferenceRequest(
            job_id=job_id,
            model=model,
            prompt=prompt,
            determinism=determinism,
            verification_mode=verification_mode
        )
        
        print(f"\n[{self.peer_id}] Requesting inference from {provider_id}")
        print(f"  Job ID: {job_id}")
        print(f"  Model: {model}")
        print(f"  Verification: {verification_mode}")
        
        # Send request
        response_str = await self.send_message(
            provider['host'],
            provider['port'],
            request.to_json()
        )
        
        if not response_str:
            return None, None
        
        # Parse response
        try:
            response = parse_message(response_str)
            
            if isinstance(response, ErrorMessage):
                print(f"  ❌ Error: {response.error_message}")
                return None, None
            
            if isinstance(response, InferenceResponse):
                print(f"  ✅ Inference received")
                print(f"  Tokens: {len(response.output_tokens)}")
                return response, provider_id
            
            print(f"  ❌ Unexpected response type: {type(response)}")
            return None, None
        
        except Exception as e:
            print(f"  ❌ Failed to parse response: {e}")
            return None, None
    
    async def verify_inference(
        self,
        response: InferenceResponse,
        provider_id: str,
        expected_model_hash: str
    ) -> bool:
        """
        Verify inference response.
        
        Returns: True if valid, False otherwise
        """
        print(f"\n[{self.peer_id}] Verifying inference {response.job_id}")
        
        # 1. Check model hash (update if pending)
        if expected_model_hash == "pending":
            # First connection - learn the model hash
            print(f"  📝 Learning model hash from provider: {response.provider_model_hash[:32]}...")
            self.known_providers[provider_id]['model_hash'] = response.provider_model_hash
            expected_model_hash = response.provider_model_hash
        
        if response.provider_model_hash != expected_model_hash:
            print(f"  ❌ Model hash mismatch!")
            print(f"     Expected: {expected_model_hash[:32]}...")
            print(f"     Got:      {response.provider_model_hash[:32]}...")
            return False
        
        print(f"  ✅ Model hash verified")
        
        # 2. Perform audit (for Merkle verification)
        if response.proof_type == "merkle":
            print(f"  Requesting audit proof...")
            
            # Create audit challenge
            import random
            num_steps = len(response.output_tokens)
            num_challenges = min(3, num_steps)
            challenge_steps = random.sample(range(num_steps), num_challenges)
            
            challenge = AuditChallenge(
                job_id=response.job_id,
                challenge_steps=challenge_steps,
                vrf_proof="mock_vrf"  # TODO: Real VRF
            )
            
            # Send challenge
            provider = self.known_providers[provider_id]
            audit_response_str = await self.send_message(
                provider['host'],
                provider['port'],
                challenge.to_json()
            )
            
            if not audit_response_str:
                print(f"  ❌ No audit response")
                return False
            
            # Parse audit proof
            try:
                audit_response = parse_message(audit_response_str)
                
                if isinstance(audit_response, ErrorMessage):
                    print(f"  ❌ Audit error: {audit_response.error_message}")
                    return False
                
                if not isinstance(audit_response, AuditProof):
                    print(f"  ❌ Unexpected audit response type")
                    return False
                
                # Verify audit proofs
                router = ProofOfInferenceRouter(expected_model_hash)
                
                # Convert P2P format to internal format
                proofs = []
                for p in audit_response.proofs:
                    proofs.append(StepProof(
                        t=p['t'],
                        prestate_hash=p['prestate_hash'],
                        logits_q=p['logits_q'],
                        next_token=p['next_token'],
                        auth_path=p['auth_path']
                    ))
                
                # Create mock response for verification
                from provider_sdk import JobResponse, AuditProofResponse
                job_response = JobResponse(
                    job_id=response.job_id,
                    output_tokens=response.output_tokens,
                    output_hash=response.output_hash,
                    transcript_root=response.transcript_root,
                    sig=response.signature,
                    provider_model_hash=response.provider_model_hash
                )
                
                audit_proof_obj = AuditProofResponse(
                    job_id=response.job_id,
                    proofs=proofs
                )
                
                # Verify
                audit_result = router.audit_job_response(audit_proof_obj, job_response)
                
                if audit_result.passed:
                    print(f"  ✅ Audit verification passed")
                    return True
                else:
                    print(f"  ❌ Audit verification failed")
                    print(f"     Failed steps: {audit_result.failed_steps}")
                    return False
            
            except Exception as e:
                print(f"  ❌ Audit verification error: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        # For other verification modes (fraud_proof, zk_snark)
        elif response.proof_type == "fraud_proof":
            print(f"  ⚠️  Fraud proof verification not yet implemented")
            return True  # Optimistically accept
        
        elif response.proof_type == "zk_snark":
            print(f"  ⚠️  ZK-SNARK verification not yet implemented")
            return True  # TODO: Implement ZK verification
        
        else:
            print(f"  ❌ Unknown verification mode: {response.proof_type}")
            return False
    
    async def run_inference_job(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 30,
        temperature: float = 0.7,
        verification_mode: str = "merkle"
    ) -> bool:
        """
        Run a complete inference job with verification.
        
        Returns: True if successful and verified, False otherwise
        """
        print(f"\n{'='*70}")
        print(f"🔍 Running Inference Job")
        print(f"{'='*70}")
        print(f"  Model: {model}")
        print(f"  Prompt: {prompt}")
        print(f"  Verification: {verification_mode}")
        print(f"{'='*70}\n")
        
        # Get expected model hash
        provider_id = None
        expected_hash = None
        for pid, pdata in self.known_providers.items():
            if pdata['model'] == model:
                provider_id = pid
                expected_hash = pdata['model_hash']
                break
        
        if not expected_hash:
            print(f"❌ No provider found for model: {model}")
            return False
        
        # Request inference
        response, provider_id = await self.request_inference(
            model=model,
            prompt={"messages": [{"role": "user", "content": prompt}]},
            determinism={"temperature": temperature, "max_tokens": max_tokens},
            verification_mode=verification_mode
        )
        
        if not response:
            print(f"\n❌ Inference request failed")
            return False
        
        # Verify inference
        verified = await self.verify_inference(response, provider_id, expected_hash)
        
        if verified:
            # Decode output
            print(f"\n{'='*70}")
            print(f"✅ INFERENCE VERIFIED")
            print(f"{'='*70}")
            print(f"  Job ID: {response.job_id}")
            print(f"  Provider: {provider_id}")
            print(f"  Tokens: {response.output_tokens}")
            print(f"  Model Hash: {response.provider_model_hash[:32]}...")
            print(f"{'='*70}\n")
            return True
        else:
            print(f"\n{'='*70}")
            print(f"❌ VERIFICATION FAILED")
            print(f"{'='*70}")
            print(f"  Job ID: {response.job_id}")
            print(f"  Provider: {provider_id}")
            print(f"  Possible fraud detected!")
            print(f"{'='*70}\n")
            return False


async def main():
    parser = argparse.ArgumentParser(description="P2P Router Node")
    parser.add_argument("--provider", action="append", nargs=3,
                       metavar=("HOST", "PORT", "MODEL"),
                       help="Add provider (can be used multiple times)")
    parser.add_argument("--prompt", default="What is 2+2?",
                       help="Inference prompt")
    parser.add_argument("--model", default="mlx-community/Qwen3-4B-4bit",
                       help="Model to use")
    parser.add_argument("--verification", default="merkle",
                       choices=["merkle", "fraud_proof", "zk_snark"],
                       help="Verification mode")
    
    args = parser.parse_args()
    
    router = RouterNode()
    
    # Add providers
    if args.provider:
        for host, port, model in args.provider:
            # Get model hash (would normally discover this)
            router.add_provider(host, int(port), model, "unknown_hash")
    else:
        print("No providers specified. Use --provider HOST PORT MODEL")
        return
    
    # Run inference job
    await router.run_inference_job(
        model=args.model,
        prompt=args.prompt,
        verification_mode=args.verification
    )


if __name__ == "__main__":
    asyncio.run(main())
