#!/usr/bin/env python3
"""
Provider Node for P2P Proof-of-Inference Network

Runs an AI model and serves inference requests over P2P network.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import asyncio
import argparse
import uuid
import time
import hashlib
from typing import Dict, Optional

from provider_sdk import ProofOfInferenceProvider
from router import ProofOfInferenceRouter
from p2p_protocol import (
    InferenceRequest, InferenceResponse, AuditChallenge, AuditProof,
    ProviderAnnounce, Heartbeat, ErrorMessage, parse_message,
    PROTOCOL_ID, MAX_MESSAGE_SIZE
)


class ProviderNode:
    """
    P2P Provider Node
    
    Serves AI inference requests and provides cryptographic proofs.
    """
    
    def __init__(self, model_path: str, host: str = "127.0.0.1", port: int = 4001):
        self.model_path = model_path
        self.host = host
        self.port = port
        self.peer_id = self._generate_peer_id()
        
        # Initialize provider
        print(f"Loading model: {model_path}")
        self.provider = ProofOfInferenceProvider(model_path, private_key=self.peer_id)
        
        # Active jobs
        self.active_jobs: Dict[str, any] = {}
        
        # Server
        self.server: Optional[asyncio.Server] = None
        self.running = False
        
        print(f"Provider Node initialized")
        print(f"  Peer ID: {self.peer_id}")
        print(f"  Model: {model_path}")
        print(f"  Model Hash: {self.provider.model_hash[:32]}...")
        print(f"  Address: {host}:{port}")
    
    def _generate_peer_id(self) -> str:
        """Generate unique peer ID."""
        return hashlib.sha256(f"{self.model_path}{time.time()}".encode()).hexdigest()[:16]
    
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming connection."""
        addr = writer.get_extra_info('peername')
        print(f"\n[{self.peer_id}] Connection from {addr}")
        
        try:
            # Read message
            data = await reader.read(MAX_MESSAGE_SIZE)
            if not data:
                return
            
            message_str = data.decode('utf-8')
            message = parse_message(message_str)
            
            # Handle message
            response = await self.handle_message(message)
            
            # Send response
            if response:
                writer.write(response.encode('utf-8'))
                await writer.drain()
        
        except Exception as e:
            print(f"[{self.peer_id}] Error handling client: {e}")
            error = ErrorMessage(
                error_code="INTERNAL_ERROR",
                error_message=str(e)
            )
            writer.write(error.to_json().encode('utf-8'))
            await writer.drain()
        
        finally:
            writer.close()
            await writer.wait_closed()
    
    async def handle_message(self, message) -> Optional[str]:
        """Handle different message types."""
        if isinstance(message, InferenceRequest):
            return await self.handle_inference_request(message)
        
        elif isinstance(message, AuditChallenge):
            return await self.handle_audit_challenge(message)
        
        elif isinstance(message, ProviderAnnounce):
            # Ignore announces from other providers
            return None
        
        elif isinstance(message, Heartbeat):
            # Respond with heartbeat
            hb = Heartbeat(
                peer_id=self.peer_id,
                timestamp=time.time(),
                active_jobs=len(self.active_jobs)
            )
            return hb.to_json()
        
        else:
            error = ErrorMessage(
                error_code="UNKNOWN_MESSAGE",
                error_message=f"Unknown message type: {type(message)}"
            )
            return error.to_json()
    
    async def handle_inference_request(self, request: InferenceRequest) -> str:
        """Process inference request."""
        print(f"\n[{self.peer_id}] Processing inference request {request.job_id}")
        print(f"  Model requested: {request.model}")
        print(f"  Verification mode: {request.verification_mode}")
        
        try:
            # Create router for this job
            router = ProofOfInferenceRouter(self.provider.model_hash)
            
            # Create job
            job = router.create_job(
                prompt=request.prompt,
                determinism=request.determinism
            )
            
            # Process inference
            print(f"  Running inference...")
            start = time.time()
            response = self.provider.process_job(job)
            inference_time = time.time() - start
            
            print(f"  ✅ Inference complete ({inference_time:.3f}s)")
            print(f"  Tokens generated: {len(response.output_tokens)}")
            
            # Store job for potential audit
            self.active_jobs[request.job_id] = {
                'job': job,
                'response': response,
                'router': router
            }
            
            # Create response
            inference_response = InferenceResponse(
                job_id=request.job_id,
                output_tokens=response.output_tokens,
                output_hash=response.output_hash,
                transcript_root=response.transcript_root,
                provider_model_hash=response.provider_model_hash,
                signature=response.sig,
                proof_type=request.verification_mode,
                proof_data=None  # Will be provided on audit
            )
            
            return inference_response.to_json()
        
        except Exception as e:
            print(f"  ❌ Inference failed: {e}")
            error = ErrorMessage(
                error_code="INFERENCE_FAILED",
                error_message=str(e),
                job_id=request.job_id
            )
            return error.to_json()
    
    async def handle_audit_challenge(self, challenge: AuditChallenge) -> str:
        """Respond to audit challenge."""
        print(f"\n[{self.peer_id}] Audit challenge for {challenge.job_id}")
        print(f"  Challenge steps: {challenge.challenge_steps}")
        
        try:
            job_data = self.active_jobs.get(challenge.job_id)
            if not job_data:
                error = ErrorMessage(
                    error_code="JOB_NOT_FOUND",
                    error_message=f"Job {challenge.job_id} not found",
                    job_id=challenge.job_id
                )
                return error.to_json()
            
            # Get the internal job ID (router's job ID, not P2P job ID)
            internal_job = job_data['job']
            
            # Create audit challenge using the internal job ID
            router = job_data['router']
            audit_challenge = router.create_audit_challenge(internal_job.job_id)
            
            # Generate audit proof
            audit_proof = self.provider.respond_to_audit(audit_challenge)
            
            # Convert to P2P format
            proofs_data = []
            for proof in audit_proof.proofs:
                proofs_data.append({
                    't': proof.t,
                    'prestate_hash': proof.prestate_hash,
                    'logits_q': proof.logits_q,
                    'next_token': proof.next_token,
                    'auth_path': proof.auth_path
                })
            
            audit_response = AuditProof(
                job_id=challenge.job_id,
                proofs=proofs_data
            )
            
            print(f"  ✅ Audit proof generated")
            return audit_response.to_json()
        
        except Exception as e:
            print(f"  ❌ Audit failed: {e}")
            error = ErrorMessage(
                error_code="AUDIT_FAILED",
                error_message=str(e),
                job_id=challenge.job_id
            )
            return error.to_json()
    
    async def start(self):
        """Start the provider node server."""
        self.server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )
        
        self.running = True
        
        addr = self.server.sockets[0].getsockname()
        print(f"\n{'='*70}")
        print(f"🚀 Provider Node Running")
        print(f"{'='*70}")
        print(f"  Peer ID: {self.peer_id}")
        print(f"  Address: {addr[0]}:{addr[1]}")
        print(f"  Model: {self.model_path}")
        print(f"  Model Hash: {self.provider.model_hash[:32]}...")
        print(f"  Protocol: {PROTOCOL_ID}")
        print(f"{'='*70}\n")
        
        async with self.server:
            await self.server.serve_forever()
    
    async def stop(self):
        """Stop the provider node."""
        self.running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        print(f"\n[{self.peer_id}] Provider node stopped")


async def main():
    parser = argparse.ArgumentParser(description="P2P Provider Node")
    parser.add_argument("--model", default="mlx-community/Qwen3-4B-4bit",
                       help="Model to serve")
    parser.add_argument("--host", default="127.0.0.1",
                       help="Host to bind to")
    parser.add_argument("--port", type=int, default=4001,
                       help="Port to listen on")
    
    args = parser.parse_args()
    
    node = ProviderNode(args.model, args.host, args.port)
    
    try:
        await node.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        await node.stop()


if __name__ == "__main__":
    asyncio.run(main())
