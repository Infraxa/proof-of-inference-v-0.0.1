#!/usr/bin/env python3
"""
Test: Can a provider cheat by using a smaller/different model?

Attack scenario:
- Router expects Qwen3-4B-4bit
- Malicious provider uses Qwen3-0.6B-4bit (faster, cheaper)
- Provider tries to fake the model hash and responses

This tests the model identity verification in Proof-of-Inference.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from provider_sdk import ProofOfInferenceProvider
from router import ProofOfInferenceRouter


def test_honest_provider():
    """Baseline: Honest provider using correct model."""
    print("\n" + "="*60)
    print("✅ HONEST PROVIDER TEST")
    print("="*60)
    
    print("\n1. Router expects: Qwen3-4B-4bit")
    honest_provider = ProofOfInferenceProvider(
        "mlx-community/Qwen3-4B-4bit",
        private_key="honest_key"
    )
    
    router = ProofOfInferenceRouter(expected_model_hash=honest_provider.model_hash)
    
    print(f"   Expected hash: {honest_provider.model_hash[:32]}...")
    
    # Create job
    prompt = {"messages": [{"role": "user", "content": "What is 2+2?"}]}
    job = router.create_job(prompt, {"temperature": 0.7, "max_tokens": 20})
    
    # Process with CORRECT model
    print("\n2. Provider processes with: Qwen3-4B-4bit")
    response = honest_provider.process_job(job)
    print(f"   Response hash: {response.transcript_root[:32]}...")
    
    # Verify
    print("\n3. Router verifies response...")
    valid = router.verify_job_response(response, provider_public_key="honest_key")
    
    if valid:
        print("   ✅ VERIFICATION PASSED - Honest provider accepted")
    else:
        print("   ❌ VERIFICATION FAILED - Something wrong!")
    
    # Audit
    print("\n4. Router audits...")
    challenge = router.create_audit_challenge(job.job_id)
    audit_proof = honest_provider.respond_to_audit(challenge)
    audit_result = router.audit_job_response(audit_proof, response)
    
    if audit_result.passed:
        print(f"   ✅ AUDIT PASSED - Provider is honest")
    else:
        print(f"   ❌ AUDIT FAILED - {audit_result.details}")
    
    return valid and audit_result.passed


def test_model_substitution_attack():
    """Attack: Provider uses cheaper 0.6B model instead of 4B."""
    print("\n" + "="*60)
    print("🚨 MODEL SUBSTITUTION ATTACK")
    print("="*60)
    
    print("\n1. Router expects: Qwen3-4B-4bit")
    # Router sets up expecting 4B model
    expected_4b_provider = ProofOfInferenceProvider(
        "mlx-community/Qwen3-4B-4bit",
        private_key="expected_key"
    )
    expected_hash = expected_4b_provider.model_hash
    
    router = ProofOfInferenceRouter(expected_model_hash=expected_hash)
    print(f"   Expected hash: {expected_hash[:32]}...")
    
    # Malicious provider loads 0.6B instead
    print("\n2. 🦹 Malicious provider secretly loads: Qwen3-0.6B-4bit")
    print("   (Trying to save compute costs!)")
    
    malicious_provider = ProofOfInferenceProvider(
        "mlx-community/Qwen3-0.6B-4bit",  # WRONG MODEL!
        private_key="malicious_key"
    )
    print(f"   Actual hash:   {malicious_provider.model_hash[:32]}...")
    
    # Create job
    prompt = {"messages": [{"role": "user", "content": "What is 2+2?"}]}
    job = router.create_job(prompt, {"temperature": 0.7, "max_tokens": 20})
    
    # Malicious provider processes with WRONG model
    print("\n3. Malicious provider generates response with 0.6B model...")
    response = malicious_provider.process_job(job)
    
    # Try to verify
    print("\n4. Router verifies response...")
    print("   Checking model hash...")
    
    valid = router.verify_job_response(response, provider_public_key="malicious_key")
    
    if valid:
        print("   ❌ VERIFICATION PASSED - Attack succeeded! (BAD)")
    else:
        print("   ✅ VERIFICATION FAILED - Attack detected! (GOOD)")
        print("   🛡️  Model hash mismatch caught the cheater!")
    
    return not valid  # Attack should be caught (return True if caught)


def test_hash_forgery_attack():
    """Attack: Provider tries to forge the model hash."""
    print("\n" + "="*60)
    print("🚨 HASH FORGERY ATTACK")
    print("="*60)
    
    print("\n1. Router expects: Qwen3-4B-4bit")
    expected_4b_provider = ProofOfInferenceProvider(
        "mlx-community/Qwen3-4B-4bit",
        private_key="expected_key"
    )
    expected_hash = expected_4b_provider.model_hash
    
    router = ProofOfInferenceRouter(expected_model_hash=expected_hash)
    print(f"   Expected hash: {expected_hash[:32]}...")
    
    # Malicious provider loads 0.6B
    print("\n2. 🦹 Malicious provider loads 0.6B but tries to fake hash...")
    malicious_provider = ProofOfInferenceProvider(
        "mlx-community/Qwen3-0.6B-4bit",
        private_key="malicious_key"
    )
    
    # Try to forge the hash
    print("   Original hash: ", malicious_provider.model_hash[:32], "...")
    malicious_provider.model_hash = expected_hash  # FORGE THE HASH!
    print("   Forged hash:   ", malicious_provider.model_hash[:32], "...")
    print("   ⚠️  Provider claims to be using 4B model!")
    
    # Create job
    prompt = {"messages": [{"role": "user", "content": "What is 2+2?"}]}
    job = router.create_job(prompt, {"temperature": 0.7, "max_tokens": 20})
    
    # Process with wrong model
    print("\n3. Provider generates response with 0.6B model...")
    response = malicious_provider.process_job(job)
    
    # Verify (hash check passes, but audit should fail)
    print("\n4. Router verifies response...")
    valid = router.verify_job_response(response, provider_public_key="malicious_key")
    
    if valid:
        print("   ⚠️  Hash verification passed (hash was forged)")
    else:
        print("   ✅ Hash verification failed")
        return True
    
    # The real test: AUDIT
    print("\n5. Router performs audit (the real test)...")
    print("   💡 Audit will catch this because:")
    print("      - 0.6B model produces different logits than 4B")
    print("      - Committed transcript won't match actual computation")
    
    challenge = router.create_audit_challenge(job.job_id)
    audit_proof = malicious_provider.respond_to_audit(challenge)
    audit_result = router.audit_job_response(audit_proof, response)
    
    if audit_result.passed:
        print("   ❌ AUDIT PASSED - Attack succeeded! (BAD)")
        return False
    else:
        print("   ✅ AUDIT FAILED - Attack detected! (GOOD)")
        print(f"   🛡️  {audit_result.details}")
        return True


def main():
    print("\n" + "="*60)
    print("🔐 PROOF-OF-INFERENCE SECURITY TEST")
    print("Testing if providers can cheat by using wrong models")
    print("="*60)
    
    results = {}
    
    # Test 1: Honest provider
    results['honest'] = test_honest_provider()
    
    # Test 2: Model substitution (should be caught by hash check)
    results['substitution'] = test_model_substitution_attack()
    
    # Test 3: Hash forgery (should be caught by audit)
    results['forgery'] = test_hash_forgery_attack()
    
    # Summary
    print("\n" + "="*60)
    print("📊 SECURITY TEST RESULTS")
    print("="*60)
    
    print(f"\n✅ Honest Provider:           {'PASSED' if results['honest'] else 'FAILED'}")
    print(f"🛡️  Model Substitution Defense: {'PASSED' if results['substitution'] else 'FAILED'}")
    print(f"🛡️  Hash Forgery Defense:      {'PASSED' if results['forgery'] else 'FAILED'}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 ALL SECURITY TESTS PASSED!")
        print("\nConclusion:")
        print("✅ Providers CANNOT cheat by using a different model")
        print("✅ Model hash verification catches substitution attacks")
        print("✅ Cryptographic audits catch hash forgery attempts")
        print("\n💡 The system successfully prevents:")
        print("   - Using cheaper/faster models to save costs")
        print("   - Faking model identity")
        print("   - Generating fake transcripts")
    else:
        print("❌ SECURITY VULNERABILITIES DETECTED!")
        print("The system failed to catch cheating attempts.")
    print("="*60)


if __name__ == "__main__":
    main()
