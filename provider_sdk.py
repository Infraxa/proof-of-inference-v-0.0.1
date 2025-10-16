"""
Proof-of-Inference Provider SDK.
Wraps mlx-lm to generate verifiable transcripts during inference.
"""

import time
from typing import List, Dict, Any, Optional, Iterator, Tuple
from dataclasses import dataclass, asdict
import json
import base64
import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Import MLX-LM
try:
    from mlx_lm import load, stream_generate
    import mlx.core as mx
    MLX_AVAILABLE = True
    print("✅ MLX-LM available - using real inference")
except ImportError as e:
    MLX_AVAILABLE = False
    print(f"⚠️  MLX-LM not available: {e}")
    print("   Note: MLX requires Python 3.9-3.12 (not 3.13 free-threaded)")
    print("   Using mock inference for demonstration...")
    
    # Mock implementations for demo
    class mx:
        @staticmethod
        def array(data):
            return np.array(data)
    
    class MockTokenizer:
        def __init__(self):
            self.chat_template = None
            self.eos_token_id = 2
            
        def encode(self, text: str) -> List[int]:
            # Simple mock: return character codes
            return [ord(c) % 1000 for c in text[:50]]
            
        def decode(self, tokens: List[int]) -> str:
            # Mock decode
            return f"Mock response: The answer is 4. (Generated {len(tokens)} tokens)"
            
        def __len__(self):
            return 32000
    
    class MockModel:
        pass
    
    def load(path: str):
        print(f"   [MOCK] Loading model: {path}")
        return MockModel(), MockTokenizer()
    
    def generate_step(prompt, model, sampler=None):
        # Mock generation - yield realistic tokens
        responses = [
            "The", " answer", " is", " ", "4", ".", " Two", " plus", " two", " equals", " four", "."
        ]
        for i, text in enumerate(responses):
            token_id = 100 + i
            logprobs = np.random.randn(32000).astype(np.float32)
            yield (token_id, logprobs)

from crypto_utils import MerkleTree, hash_data, quantize_logits, simple_sign


@dataclass
class StepArtifact:
    """Per-step data for transcript building."""
    step: int
    input_hash: str  # Hash of model state + prompt context
    logits_hash: str  # Hash of quantized logits
    token: int
    nonce: str
    
    def to_hash(self) -> str:
        """Convert to hash input."""
        return hash_data({
            "step": self.step,
            "input_hash": self.input_hash,
            "logits_hash": self.logits_hash,
            "token": self.token,
            "nonce": self.nonce
        })


@dataclass
class JobRequest:
    """Router's job specification."""
    job_id: str
    model_hash: str
    prompt: Dict[str, Any]
    determinism: Dict[str, Any]
    nonce: str
    audit_budget: Dict[str, int]


@dataclass
class JobResponse:
    """Provider's response to a job."""
    job_id: str
    output_tokens: List[int]
    output_hash: str
    transcript_root: str
    sig: str
    provider_model_hash: str  # Hash of model actually used by provider


@dataclass
class AuditChallenge:
    """Router's audit request."""
    job_id: str
    challenge_steps: List[int]
    vrf_proof: str


@dataclass
class StepProof:
    """Proof data for a single audited step."""
    t: int
    prestate_hash: str
    logits_q: str  # Base64 encoded quantized logits
    next_token: int
    auth_path: List[List[str]]  # [[hash, position], ...]


@dataclass
class AuditProof:
    """Complete audit response."""
    job_id: str
    proofs: List[StepProof]


class ProofOfInferenceProvider:
    """MLX-LM provider with transcript commitment generation."""
    
    def __init__(self, model_path: str, private_key: str):
        """Initialize with model and signing key."""
        print(f"Loading model: {model_path}")
        self.model, self.tokenizer = load(model_path)
        self.private_key = private_key
        
        # Compute model hash (simplified - in practice hash all weights)
        self.model_hash = hash_data(f"mlx-lm:{model_path}:{time.time()}")
        print(f"Model hash: {self.model_hash}")
        
        # Cache for storing logits and transcripts per job
        self.logits_cache = {}  # job_id -> {step_idx -> quantized_logits}
        self.transcript_cache = {}  # job_id -> List[StepArtifact]
    
    def process_job(self, job: JobRequest) -> JobResponse:
        """
        Process a job with full transcript generation.
        Returns commitment + signature.
        """
        print(f"Processing job {job.job_id}")
        
        # Extract parameters
        prompt_text = self._format_prompt(job.prompt)
        tokens = self.tokenizer.encode(prompt_text)
        
        # Set deterministic generation
        det = job.determinism
        sampler_kwargs = {
            "temp": det.get("temperature", 0.0),
            "top_p": det.get("top_p", 1.0),
            "min_p": det.get("min_p", 0.0),
            "top_k": det.get("top_k", -1),
        }
        
        # Generate with transcript
        transcript, output_tokens, logits_cache = self._generate_with_transcript(
            tokens, sampler_kwargs, job.nonce, max_tokens=det.get("max_tokens", 100)
        )
        
        # Store logits and transcript cache for this job
        self.logits_cache[job.job_id] = logits_cache
        self.transcript_cache[job.job_id] = transcript
        
        # Build Merkle tree
        leaves = [step.to_hash() for step in transcript]
        tree = MerkleTree(leaves)
        
        # Compute output hash
        output_hash = hash_data(output_tokens)
        
        # Sign commitment (include model hash to prevent forgery)
        message = f"{tree.root}|{output_hash}|{job.job_id}|{self.model_hash}"
        sig = simple_sign(message, self.private_key)
        
        return JobResponse(
            job_id=job.job_id,
            output_tokens=output_tokens,
            output_hash=output_hash,
            transcript_root=tree.root,
            sig=sig,
            provider_model_hash=self.model_hash  # Include actual model hash
        )
    
    def respond_to_audit(self, challenge: AuditChallenge, transcript: List[StepArtifact] = None) -> AuditProof:
        """Generate proofs for audited steps using cached real logits."""
        print(f"Responding to audit for job {challenge.job_id}")
        
        # Use cached transcript if not provided
        if transcript is None:
            transcript = self.transcript_cache.get(challenge.job_id, [])
            if not transcript:
                raise ValueError(f"No cached transcript for job {challenge.job_id}")
        
        tree = MerkleTree([step.to_hash() for step in transcript])
        proofs = []
        
        # Get cached logits for this job
        job_logits = self.logits_cache.get(challenge.job_id, {})
        
        for step_idx in challenge.challenge_steps:
            if step_idx >= len(transcript):
                continue
            
            step = transcript[step_idx]
            proof = tree.get_proof(step_idx)
            
            # Get the REAL cached logits from generation
            if step_idx in job_logits:
                logits_q = job_logits[step_idx]
            else:
                # Fallback if not cached (shouldn't happen)
                print(f"Warning: Logits not cached for step {step_idx}, using dummy")
                vocab_size = getattr(self.tokenizer, 'vocab_size', 32000)
                dummy_logits = np.random.randn(vocab_size).astype(np.float32)
                logits_q = quantize_logits(dummy_logits)
            
            logits_b64 = base64.b64encode(logits_q.tobytes()).decode()
            
            proofs.append(StepProof(
                t=step_idx,
                prestate_hash=step.input_hash,
                logits_q=logits_b64,
                next_token=step.token,
                auth_path=[list(pair) for pair in proof.auth_path]  # Convert tuples to lists
            ))
        
        return AuditProof(
            job_id=challenge.job_id,
            proofs=proofs
        )
    
    def _generate_with_transcript(self, prompt_tokens: List[int], sampler_kwargs: Dict[str, Any], 
                                nonce: str, max_tokens: int = 100) -> Tuple[List[StepArtifact], List[int], Dict[int, np.ndarray]]:
        """Generate tokens while building transcript using MLX stream_generate."""
        transcript = []
        output_tokens = []
        logits_cache = {}  # Cache quantized logits for audit
        
        # Start with initial state hash
        current_input_hash = hash_data(prompt_tokens + [nonce])
        
        # Extract sampler parameters and create sampler
        from mlx_lm.sample_utils import make_sampler
        temp = sampler_kwargs.get("temp", 0.7)
        top_p = sampler_kwargs.get("top_p", 1.0)
        sampler = make_sampler(temp=temp, top_p=top_p)
        
        # Use stream_generate for token-by-token generation
        step_count = 0
        for response in stream_generate(
            self.model,
            self.tokenizer,
            prompt=prompt_tokens,
            max_tokens=max_tokens,
            sampler=sampler
        ):
            # Get token and logprobs from response
            token_id = response.token
            logprobs = response.logprobs
            
            # Convert logprobs to numpy array for hashing
            # MLX arrays need to be converted via tolist() first
            import mlx.core as mx
            if isinstance(logprobs, mx.array):
                logits_array = np.array(logprobs.tolist(), dtype=np.float32)
            else:
                logits_array = np.array(logprobs, dtype=np.float32)
            
            # Quantize and hash logits
            logits_q = quantize_logits(logits_array)
            logits_hash = hash_data(logits_q.tobytes())
            
            # Cache the quantized logits for this step
            logits_cache[step_count] = logits_q
            
            # Create step artifact
            artifact = StepArtifact(
                step=step_count,
                input_hash=current_input_hash,
                logits_hash=logits_hash,
                token=token_id,
                nonce=nonce
            )
            
            transcript.append(artifact)
            output_tokens.append(token_id)
            
            # Update input hash for next step
            prompt_tokens.append(token_id)
            current_input_hash = hash_data(prompt_tokens + [nonce])
            
            step_count += 1
            
            # Check for EOS
            if token_id == self.tokenizer.eos_token_id:
                break
        
        return transcript, output_tokens, logits_cache
    
    def _format_prompt(self, prompt: Dict[str, Any]) -> str:
        """Convert prompt dict to text using chat template if available."""
        if isinstance(prompt, str):
            return prompt
        elif "messages" in prompt:
            # Use tokenizer's chat template if available
            messages = prompt["messages"]
            if hasattr(self.tokenizer, 'chat_template') and self.tokenizer.chat_template is not None:
                try:
                    return self.tokenizer.apply_chat_template(
                        messages, 
                        add_generation_prompt=True,
                        tokenize=False
                    )
                except Exception as e:
                    print(f"Warning: Could not apply chat template: {e}")
            
            # Fallback to simple formatting
            formatted = ""
            if prompt.get("system"):
                formatted = f"system: {prompt['system']}\n"
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                formatted += f"{role}: {content}\n"
            return formatted
        else:
            return str(prompt)
