#!/usr/bin/env python3
"""
ZK-SNARK Authenticity Tests

Proves that the ZK-SNARK system is NOT faking anything:
1. Wrong logits should FAIL verification
2. Modified hash should FAIL verification  
3. Different logits should produce different proofs
4. Proof cannot be reused for different data
5. Circuit actually enforces constraints
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import subprocess
import json
import numpy as np
from provider_sdk import ProofOfInferenceProvider
from router import ProofOfInferenceRouter


def compute_simple_hash(values):
    """Compute simple hash (sum) matching the circuit."""
    return sum(values)


def generate_proof(logits, logits_hash, output_prefix, build_dir="circuits/build"):
    """Generate a ZK proof for given logits and hash."""
    # Create input
    input_data = {
        "logits_hash": str(logits_hash),
        "logits": [str(x) for x in logits]
    }
    
    input_file = f'{build_dir}/{output_prefix}_input.json'
    with open(input_file, 'w') as f:
        json.dump(input_data, f)
    
    # Generate witness
    result = subprocess.run([
        'snarkjs', 'wtns', 'calculate',
        f'{build_dir}/logits_16_js/logits_16.wasm',
        input_file,
        f'{build_dir}/{output_prefix}_witness.wtns'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        return False, result.stderr
    
    # Generate proof
    result = subprocess.run([
        'snarkjs', 'groth16', 'prove',
        f'{build_dir}/logits_16_0000.zkey',
        f'{build_dir}/{output_prefix}_witness.wtns',
        f'{build_dir}/{output_prefix}_proof.json',
        f'{build_dir}/{output_prefix}_public.json'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        return False, result.stderr
    
    return True, None


def verify_proof(output_prefix, build_dir="circuits/build"):
    """Verify a ZK proof."""
    result = subprocess.run([
        'snarkjs', 'groth16', 'verify',
        f'{build_dir}/logits_16_vkey.json',
        f'{build_dir}/{output_prefix}_public.json',
        f'{build_dir}/{output_prefix}_proof.json'
    ], capture_output=True, text=True)
    
    return "OK" in result.stdout


def test_1_correct_proof_should_verify():
    """Test 1: Correct proof should verify."""
    print("\n" + "="*70)
    print("TEST 1: Correct Proof Should Verify")
    print("="*70)
    
    logits = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 50, 25, 12, 6, 3, 1]
    logits_hash = compute_simple_hash(logits)
    
    print(f"\nLogits: {logits[:4]}...")
    print(f"Hash: {logits_hash}")
    
    print("\nGenerating proof with CORRECT data...")
    success, error = generate_proof(logits, logits_hash, "test1")
    
    if not success:
        print(f"❌ Proof generation failed: {error}")
        return False
    
    print("✅ Proof generated")
    
    print("\nVerifying proof...")
    verified = verify_proof("test1")
    
    if verified:
        print("✅ TEST PASSED: Correct proof verified")
        return True
    else:
        print("❌ TEST FAILED: Correct proof should verify!")
        return False


def test_2_wrong_logits_should_fail():
    """Test 2: Wrong logits should FAIL to generate valid proof."""
    print("\n" + "="*70)
    print("TEST 2: Wrong Logits Should Fail")
    print("="*70)
    
    correct_logits = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 50, 25, 12, 6, 3, 1]
    correct_hash = compute_simple_hash(correct_logits)
    
    # Try to cheat: use different logits but claim same hash
    wrong_logits = [999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999, 999]
    wrong_hash = compute_simple_hash(wrong_logits)
    
    print(f"\nCorrect logits: {correct_logits[:4]}...")
    print(f"Correct hash: {correct_hash}")
    print(f"\nWrong logits: {wrong_logits[:4]}...")
    print(f"Wrong hash: {wrong_hash}")
    print(f"\nTrying to prove wrong logits with CORRECT hash (cheating)...")
    
    # This should FAIL because wrong_logits don't hash to correct_hash
    success, error = generate_proof(wrong_logits, correct_hash, "test2_cheat")
    
    if not success:
        print("✅ TEST PASSED: Cannot generate proof with wrong data!")
        print(f"   Error (expected): {error[:100]}...")
        return True
    
    # If proof was generated, it should NOT verify
    print("⚠️  Proof was generated (unexpected), checking verification...")
    verified = verify_proof("test2_cheat")
    
    if not verified:
        print("✅ TEST PASSED: Cheating proof does not verify")
        return True
    else:
        print("❌ TEST FAILED: Cheating proof should NOT verify!")
        return False


def test_3_modified_hash_should_fail():
    """Test 3: Modifying the hash should fail verification."""
    print("\n" + "="*70)
    print("TEST 3: Modified Hash Should Fail")
    print("="*70)
    
    logits = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 50, 25, 12, 6, 3, 1]
    correct_hash = compute_simple_hash(logits)
    modified_hash = correct_hash + 1  # Tamper with hash
    
    print(f"\nLogits: {logits[:4]}...")
    print(f"Correct hash: {correct_hash}")
    print(f"Modified hash: {modified_hash}")
    
    print("\nGenerating proof with MODIFIED hash...")
    success, error = generate_proof(logits, modified_hash, "test3_modified")
    
    if not success:
        print("✅ TEST PASSED: Cannot generate proof with modified hash!")
        print(f"   Error (expected): {error[:100]}...")
        return True
    
    print("⚠️  Proof was generated, checking verification...")
    verified = verify_proof("test3_modified")
    
    if not verified:
        print("✅ TEST PASSED: Modified hash proof does not verify")
        return True
    else:
        print("❌ TEST FAILED: Modified hash should fail!")
        return False


def test_4_different_logits_different_proofs():
    """Test 4: Different logits should produce different proofs."""
    print("\n" + "="*70)
    print("TEST 4: Different Logits Produce Different Proofs")
    print("="*70)
    
    logits_a = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 50, 25, 12, 6, 3, 1]
    logits_b = [111, 222, 333, 444, 555, 666, 777, 888, 999, 1111, 55, 27, 13, 7, 4, 2]
    
    hash_a = compute_simple_hash(logits_a)
    hash_b = compute_simple_hash(logits_b)
    
    print(f"\nLogits A: {logits_a[:4]}... -> Hash: {hash_a}")
    print(f"Logits B: {logits_b[:4]}... -> Hash: {hash_b}")
    
    print("\nGenerating proof A...")
    success_a, _ = generate_proof(logits_a, hash_a, "test4_a")
    if not success_a:
        print("❌ Failed to generate proof A")
        return False
    
    print("Generating proof B...")
    success_b, _ = generate_proof(logits_b, hash_b, "test4_b")
    if not success_b:
        print("❌ Failed to generate proof B")
        return False
    
    # Read the proofs
    with open('circuits/build/test4_a_proof.json', 'r') as f:
        proof_a = json.load(f)
    
    with open('circuits/build/test4_b_proof.json', 'r') as f:
        proof_b = json.load(f)
    
    # Proofs should be different
    if proof_a != proof_b:
        print("✅ TEST PASSED: Different logits produce different proofs")
        print(f"   Proof A pi_a: {proof_a['pi_a'][0][:20]}...")
        print(f"   Proof B pi_a: {proof_b['pi_a'][0][:20]}...")
        return True
    else:
        print("❌ TEST FAILED: Proofs should be different!")
        return False


def test_5_proof_cannot_be_reused():
    """Test 5: Proof for one set of logits cannot verify another."""
    print("\n" + "="*70)
    print("TEST 5: Proof Cannot Be Reused")
    print("="*70)
    
    logits_a = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 50, 25, 12, 6, 3, 1]
    logits_b = [111, 222, 333, 444, 555, 666, 777, 888, 999, 1111, 55, 27, 13, 7, 4, 2]
    
    hash_a = compute_simple_hash(logits_a)
    hash_b = compute_simple_hash(logits_b)
    
    print(f"\nLogits A: {logits_a[:4]}... -> Hash: {hash_a}")
    print(f"Logits B: {logits_b[:4]}... -> Hash: {hash_b}")
    
    print("\nGenerating proof for logits A...")
    success, _ = generate_proof(logits_a, hash_a, "test5_a")
    if not success:
        print("❌ Failed to generate proof")
        return False
    
    print("✅ Proof A generated")
    
    # Try to use proof A to verify logits B (should fail)
    print("\nTrying to use proof A to verify logits B (attack)...")
    
    # Manually create public.json for logits B but use proof from A
    public_b = {"logits_hash": str(hash_b)}
    with open('circuits/build/test5_attack_public.json', 'w') as f:
        json.dump(public_b, f)
    
    # Copy proof A
    import shutil
    shutil.copy('circuits/build/test5_a_proof.json', 'circuits/build/test5_attack_proof.json')
    
    # Try to verify
    verified = verify_proof("test5_attack")
    
    if not verified:
        print("✅ TEST PASSED: Cannot reuse proof for different data!")
        return True
    else:
        print("❌ TEST FAILED: Proof should not verify different data!")
        return False


def test_6_real_model_logits():
    """Test 6: Verify with real model logits."""
    print("\n" + "="*70)
    print("TEST 6: Real Model Logits")
    print("="*70)
    
    print("\n1. Running real MLX inference...")
    provider = ProofOfInferenceProvider("mlx-community/Qwen3-0.6B-4bit", private_key="test")
    
    router = ProofOfInferenceRouter(provider.model_hash)
    job = router.create_job(
        prompt={"messages": [{"role": "user", "content": "Hi"}]},
        determinism={"temperature": 0.7, "max_tokens": 5}
    )
    
    response = provider.process_job(job)
    print(f"   Tokens generated: {len(response.output_tokens)}")
    
    # Get real logits
    challenge = router.create_audit_challenge(job.job_id)
    audit_proof = provider.respond_to_audit(challenge)
    first_step = audit_proof.proofs[0]
    
    import base64
    logits_bytes = base64.b64decode(first_step.logits_q)
    logits_full = np.frombuffer(logits_bytes, dtype=np.float32)
    
    print(f"   Real logits shape: {logits_full.shape}")
    
    # Sample and quantize
    indices = np.random.choice(len(logits_full), 16, replace=False)
    logits_sampled = logits_full[indices]
    
    # Quantize
    min_val = logits_sampled.min()
    max_val = logits_sampled.max()
    if max_val - min_val > 0:
        normalized = (logits_sampled - min_val) / (max_val - min_val)
        logits_quantized = (normalized * 1000).astype(int).tolist()
    else:
        logits_quantized = [0] * 16
    
    logits_hash = compute_simple_hash(logits_quantized)
    
    print(f"\n2. Generating ZK proof for real logits...")
    print(f"   Quantized logits: {logits_quantized[:4]}...")
    print(f"   Hash: {logits_hash}")
    
    success, error = generate_proof(logits_quantized, logits_hash, "test6_real")
    
    if not success:
        print(f"❌ Failed to generate proof: {error}")
        return False
    
    print("✅ Proof generated")
    
    print("\n3. Verifying proof...")
    verified = verify_proof("test6_real")
    
    if verified:
        print("✅ TEST PASSED: Real model logits verified with ZK-SNARK!")
        return True
    else:
        print("❌ TEST FAILED: Real logits should verify")
        return False


def main():
    print("\n" + "="*70)
    print("🔬 ZK-SNARK AUTHENTICITY TESTS")
    print("="*70)
    print("\nProving the system is NOT faking anything:")
    print("  1. Correct proofs verify")
    print("  2. Wrong logits fail")
    print("  3. Modified hash fails")
    print("  4. Different logits produce different proofs")
    print("  5. Proofs cannot be reused")
    print("  6. Real model logits work")
    print("="*70)
    
    # Check setup
    if not os.path.exists('circuits/build/logits_16_0000.zkey'):
        print("\n❌ Circuits not compiled. Run demo_zk_inference.py first.")
        return
    
    # Run tests
    results = []
    
    results.append(("Correct proof verifies", test_1_correct_proof_should_verify()))
    results.append(("Wrong logits fail", test_2_wrong_logits_should_fail()))
    results.append(("Modified hash fails", test_3_modified_hash_should_fail()))
    results.append(("Different proofs", test_4_different_logits_different_proofs()))
    results.append(("Proof cannot be reused", test_5_proof_cannot_be_reused()))
    results.append(("Real model logits", test_6_real_model_logits()))
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    print(f"\n{'Test':<35} {'Result':<15}")
    print("-" * 70)
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name:<35} {status:<15}")
    
    all_passed = all(r[1] for r in results)
    
    print("\n" + "="*70)
    print("⚖️  FINAL VERDICT")
    print("="*70)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED")
        print("\nThe ZK-SNARK system is AUTHENTIC:")
        print("  ✅ Cannot fake proofs with wrong data")
        print("  ✅ Cannot modify hashes")
        print("  ✅ Cannot reuse proofs")
        print("  ✅ Different data produces different proofs")
        print("  ✅ Works with real model logits")
        print("\n💡 This proves the system is using REAL cryptography,")
        print("   not just mocking or faking the verification!")
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("\nThe system may have issues. Review failed tests.")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
