#!/usr/bin/env python3
"""
Proof-of-Inference Demo
Shows end-to-end verifiable inference using mlx-lm.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import json
import time
from provider_sdk import ProofOfInferenceProvider
from router import ProofOfInferenceRouter


def main():
    print("🚀 Proof-of-Inference Demo")
    print("=" * 50)
    
    # Initialize provider
    print("\n1. Initializing Provider...")
    model_path = "mlx-community/Qwen3-4B-4bit"  # 4-bit quantized Qwen3 model
    print(f"   Model will be downloaded from Hugging Face if not cached...")
    provider = ProofOfInferenceProvider(model_path, private_key="provider_secret_key")
    
    # Initialize router
    print("2. Initializing Router...")
    router = ProofOfInferenceRouter(expected_model_hash=provider.model_hash)
    
    # Create a job
    print("\n3. Creating Job...")
    prompt = {
        "messages": [
            {"role": "user", "content": "What is 2+2? Answer in one short sentence."}
        ]
    }
    job = router.create_job(prompt, {"temperature": 0.7, "max_tokens": 30})
    print(f"Job created: {job.job_id}")
    print(f"Model hash: {job.model_hash}")
    print(f"Nonce: {job.nonce}")
    
    # Provider processes job
    print("\n4. Provider Processing Job...")
    start_time = time.time()
    response = provider.process_job(job)
    process_time = time.time() - start_time
    print(f"   Processing time: {process_time:.2f}s")
    print(f"   Output tokens: {len(response.output_tokens)}")
    print(f"   Transcript root: {response.transcript_root[:16]}...")
    
    # Router verifies response
    print("\n5. Router Verifying Response...")
    valid = router.verify_job_response(response, provider_public_key="provider_secret_key")
    if not valid:
        print("❌ Response verification failed!")
        return
    
    print("✅ Response verification passed")
    
    # Decide whether to audit
    should_audit = router.should_audit_job(job.job_id)
    print(f"\n6. Audit Decision: {'YES' if should_audit else 'NO'}")
    
    # For demo purposes, force an audit
    if not should_audit:
        print("   (Forcing audit for demo)")
        should_audit = True
    
    if should_audit:
        print("7. Creating Audit Challenge...")
        challenge = router.create_audit_challenge(job.job_id)
        print(f"Challenge steps: {challenge.challenge_steps}")
        
        # Provider responds to audit using cached transcript and logits
        print("8. Provider Generating Audit Proof...")
        audit_proof = provider.respond_to_audit(challenge)  # Uses cached data
        
        # Router audits
        print("9. Router Performing Audit...")
        audit_result = router.audit_job_response(audit_proof, response)
        
        if audit_result.passed:
            print("✅ Audit PASSED - Provider verified!")
        else:
            print(f"❌ Audit FAILED - {audit_result.details}")
    
    # Decode and show output
    print("\n10. Final Output:")
    output_text = provider.tokenizer.decode(response.output_tokens)
    print(f"Response: {output_text}")
    
    print("\n" + "=" * 50)
    print("🎉 Demo Complete!")
    print(f"Total time: {time.time() - start_time:.2f}s")
    print("\nKey Security Properties:")
    print("• Model identity verified via hash")
    print("• Execution committed via Merkle tree")
    print("• Selective audit with VRF")
    print("• Cryptographic binding prevents spoofing")


if __name__ == "__main__":
    main()
