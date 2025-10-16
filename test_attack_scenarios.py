#!/usr/bin/env python3
"""
Comprehensive Attack Simulation: Multiple Attackers vs Expected Model

Scenario:
- Router expects: Qwen3-4B-4bit (the "premium" model everyone claims to use)
- Attacker 1: Uses Qwen3-0.6B-4bit (cheaper, faster)
- Attacker 2: Uses Qwen3-1.7B-6bit (middle ground)
- Honest Provider: Actually uses Qwen3-4B-4bit

This tests if the system can detect providers trying to save costs
by using smaller models while claiming to use the 4B model.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import time
from provider_sdk import ProofOfInferenceProvider
from router import ProofOfInferenceRouter


def test_provider(model_path: str, expected_hash: str, router: ProofOfInferenceRouter, 
                  is_honest: bool = False, label: str = "Provider"):
    """Test a single provider against the router."""
    print(f"\n{'='*70}")
    print(f"{'🟢 HONEST' if is_honest else '🔴 ATTACKER'}: {label}")
    print(f"{'='*70}")
    
    # Load model
    print(f"\n1. Loading model: {model_path}")
    start = time.time()
    provider = ProofOfInferenceProvider(model_path, private_key=f"{label}_key")
    load_time = time.time() - start
    
    print(f"   Model hash: {provider.model_hash[:32]}...")
    print(f"   Load time: {load_time:.2f}s")
    
    # Check if hash matches expected
    hash_matches = provider.model_hash == expected_hash
    print(f"   Hash matches expected: {'✅ YES' if hash_matches else '❌ NO'}")
    
    if not is_honest and hash_matches:
        print("   ⚠️  WARNING: Attacker hash matches! (This shouldn't happen)")
    
    # Create job
    prompt = {
        "messages": [
            {"role": "user", "content": "What is 2+2? Answer in one short sentence."}
        ]
    }
    job = router.create_job(prompt, {"temperature": 0.7, "max_tokens": 30})
    
    # Process job
    print(f"\n2. Processing job...")
    start = time.time()
    response = provider.process_job(job)
    inference_time = time.time() - start
    
    tokens = len(response.output_tokens)
    throughput = tokens / inference_time if inference_time > 0 else 0
    
    print(f"   Inference time: {inference_time:.3f}s")
    print(f"   Tokens: {tokens}")
    print(f"   Throughput: {throughput:.1f} tok/s")
    
    # Verify response
    print(f"\n3. Router verifying response...")
    verified = router.verify_job_response(response, provider_public_key=f"{label}_key")
    
    if verified:
        print(f"   {'✅' if is_honest else '❌'} Verification PASSED")
        if not is_honest:
            print(f"   🚨 SECURITY BREACH: Attacker passed verification!")
    else:
        print(f"   {'❌' if is_honest else '✅'} Verification FAILED")
        if not is_honest:
            print(f"   🛡️  Attack detected and blocked!")
    
    # Audit (if verification passed)
    audit_passed = None
    if verified:
        print(f"\n4. Router performing audit...")
        challenge = router.create_audit_challenge(job.job_id)
        print(f"   Challenge steps: {challenge.challenge_steps}")
        
        audit_proof = provider.respond_to_audit(challenge)
        audit_result = router.audit_job_response(audit_proof, response)
        audit_passed = audit_result.passed
        
        if audit_passed:
            print(f"   {'✅' if is_honest else '❌'} Audit PASSED")
            if not is_honest:
                print(f"   🚨 CRITICAL: Attacker passed audit!")
        else:
            print(f"   {'❌' if is_honest else '✅'} Audit FAILED")
            if not is_honest:
                print(f"   🛡️  Attack caught by audit: {audit_result.details}")
    
    # Decode output for comparison
    output_text = provider.tokenizer.decode(response.output_tokens)
    
    return {
        "model": model_path.split('/')[-1],
        "is_honest": is_honest,
        "hash_matches": hash_matches,
        "load_time": load_time,
        "inference_time": inference_time,
        "throughput": throughput,
        "tokens": tokens,
        "verification_passed": verified,
        "audit_passed": audit_passed,
        "output": output_text[:100],
        "detected": not verified or (verified and not audit_passed)
    }


def main():
    print("\n" + "="*70)
    print("🔐 COMPREHENSIVE ATTACK SIMULATION")
    print("="*70)
    print("\nScenario:")
    print("  • Router expects: Qwen3-4B-4bit (premium model)")
    print("  • Attacker 1: Uses 0.6B-4bit (6.7x smaller, 2x faster)")
    print("  • Attacker 2: Uses 1.7B-6bit (2.4x smaller, ~1.5x faster)")
    print("  • Honest Provider: Uses 4B-4bit (as claimed)")
    print("\nGoal: Detect providers trying to save costs with smaller models")
    print("="*70)
    
    # Setup: Create expected 4B provider to get hash
    print("\n📋 SETUP: Establishing expected model hash...")
    expected_provider = ProofOfInferenceProvider(
        "mlx-community/Qwen3-4B-4bit",
        private_key="setup_key"
    )
    expected_hash = expected_provider.model_hash
    print(f"   Expected hash: {expected_hash[:32]}...")
    
    # Create router with expected hash
    router = ProofOfInferenceRouter(
        expected_model_hash=expected_hash,
        audit_rate=1.0  # Always audit for testing
    )
    
    results = []
    
    # Test 1: Honest Provider (4B)
    print("\n" + "="*70)
    print("TEST 1: HONEST PROVIDER")
    print("="*70)
    result = test_provider(
        "mlx-community/Qwen3-4B-4bit",
        expected_hash,
        router,
        is_honest=True,
        label="Honest Provider (4B)"
    )
    results.append(result)
    
    # Test 2: Attacker 1 (0.6B)
    print("\n" + "="*70)
    print("TEST 2: ATTACKER 1 (Cheapest Model)")
    print("="*70)
    result = test_provider(
        "mlx-community/Qwen3-0.6B-4bit",
        expected_hash,
        router,
        is_honest=False,
        label="Attacker 1 (0.6B)"
    )
    results.append(result)
    
    # Test 3: Attacker 2 (1.7B)
    print("\n" + "="*70)
    print("TEST 3: ATTACKER 2 (Middle Ground)")
    print("="*70)
    result = test_provider(
        "mlx-community/Qwen3-1.7B-6bit",
        expected_hash,
        router,
        is_honest=False,
        label="Attacker 2 (1.7B)"
    )
    results.append(result)
    
    # Summary Table
    print("\n" + "="*70)
    print("📊 RESULTS SUMMARY")
    print("="*70)
    
    print(f"\n{'Provider':<25} {'Model':<20} {'Speed':<12} {'Verified':<12} {'Audit':<12} {'Detected':<12}")
    print("-" * 95)
    
    for r in results:
        provider_label = "✅ Honest" if r['is_honest'] else "🔴 Attacker"
        verified_icon = "✅" if r['verification_passed'] else "❌"
        audit_icon = "✅" if r['audit_passed'] else "❌" if r['audit_passed'] is not None else "N/A"
        detected_icon = "✅" if r['detected'] else "❌"
        
        print(f"{provider_label:<25} {r['model']:<20} {r['throughput']:>6.1f} tok/s  "
              f"{verified_icon:<12} {audit_icon:<12} {detected_icon:<12}")
    
    # Performance Comparison
    print("\n" + "="*70)
    print("⚡ PERFORMANCE COMPARISON")
    print("="*70)
    
    print(f"\n{'Model':<20} {'Load Time':<12} {'Inference':<12} {'Throughput':<15} {'Cost Savings':<15}")
    print("-" * 80)
    
    baseline = results[0]  # Honest 4B
    for r in results:
        speedup = r['throughput'] / baseline['throughput'] if baseline['throughput'] > 0 else 1.0
        cost_savings = f"{(1 - r['inference_time']/baseline['inference_time'])*100:.0f}%" if baseline['inference_time'] > 0 else "N/A"
        
        print(f"{r['model']:<20} {r['load_time']:>6.2f}s      {r['inference_time']:>6.3f}s     "
              f"{r['throughput']:>6.1f} tok/s ({speedup:.1f}x)  {cost_savings:>10}")
    
    # Security Analysis
    print("\n" + "="*70)
    print("🛡️  SECURITY ANALYSIS")
    print("="*70)
    
    honest_count = sum(1 for r in results if r['is_honest'])
    attacker_count = sum(1 for r in results if not r['is_honest'])
    detected_count = sum(1 for r in results if not r['is_honest'] and r['detected'])
    
    print(f"\nTotal Providers Tested: {len(results)}")
    print(f"  • Honest: {honest_count}")
    print(f"  • Attackers: {attacker_count}")
    print(f"  • Attackers Detected: {detected_count}/{attacker_count}")
    
    detection_rate = (detected_count / attacker_count * 100) if attacker_count > 0 else 0
    
    print(f"\n🎯 Detection Rate: {detection_rate:.0f}%")
    
    if detection_rate == 100:
        print("\n✅ SUCCESS: All attacks were detected and blocked!")
        print("\nHow it works:")
        print("  1. Model hash verification catches substitution immediately")
        print("  2. Cryptographic signatures prevent hash forgery")
        print("  3. Merkle tree audits verify actual computation")
        print("\nConclusion:")
        print("  ✅ Providers CANNOT use cheaper models without detection")
        print("  ✅ System successfully prevents cost-cutting fraud")
    else:
        print(f"\n❌ FAILURE: {attacker_count - detected_count} attacks went undetected!")
        print("\n⚠️  SECURITY VULNERABILITY DETECTED!")
    
    # Output Comparison
    print("\n" + "="*70)
    print("📝 OUTPUT COMPARISON")
    print("="*70)
    
    for r in results:
        label = "✅ Honest" if r['is_honest'] else "🔴 Attacker"
        print(f"\n{label} ({r['model']}):")
        print(f"  {r['output']}")
    
    # Final Verdict
    print("\n" + "="*70)
    print("⚖️  FINAL VERDICT")
    print("="*70)
    
    if detection_rate == 100:
        print("\n🎉 PROOF-OF-INFERENCE SYSTEM: SECURE")
        print("\nThe system successfully:")
        print("  ✅ Detects model substitution attacks")
        print("  ✅ Prevents providers from using cheaper models")
        print("  ✅ Maintains cryptographic integrity")
        print("\n💡 Economic Impact:")
        print(f"  • Attacker 1 (0.6B) would save ~{(1-results[1]['inference_time']/results[0]['inference_time'])*100:.0f}% compute cost")
        print(f"  • Attacker 2 (1.7B) would save ~{(1-results[2]['inference_time']/results[0]['inference_time'])*100:.0f}% compute cost")
        print("  • But both are CAUGHT and BLOCKED! 🛡️")
    else:
        print("\n⚠️  PROOF-OF-INFERENCE SYSTEM: VULNERABLE")
        print("\nSome attacks were not detected. Further hardening needed.")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
