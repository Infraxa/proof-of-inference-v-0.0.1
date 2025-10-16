#!/usr/bin/env python3
"""
Compare different MLX models for Proof-of-Inference performance.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import time
from provider_sdk import ProofOfInferenceProvider
from router import ProofOfInferenceRouter


def benchmark_model(model_path: str, prompt: dict, max_tokens: int = 30):
    """Benchmark a single model."""
    print(f"\n{'='*60}")
    print(f"Testing: {model_path}")
    print(f"{'='*60}")
    
    # Initialize provider
    start_init = time.time()
    provider = ProofOfInferenceProvider(model_path, private_key="test_key")
    init_time = time.time() - start_init
    
    # Initialize router
    router = ProofOfInferenceRouter(expected_model_hash=provider.model_hash)
    
    # Create job
    job = router.create_job(prompt, {"temperature": 0.7, "max_tokens": max_tokens})
    
    # Process job (inference + transcript generation)
    start_inference = time.time()
    response = provider.process_job(job)
    inference_time = time.time() - start_inference
    
    # Verify response
    start_verify = time.time()
    valid = router.verify_job_response(response, provider_public_key="test_key")
    verify_time = time.time() - start_verify
    
    # Create and respond to audit
    challenge = router.create_audit_challenge(job.job_id)
    
    start_audit = time.time()
    audit_proof = provider.respond_to_audit(challenge)
    audit_gen_time = time.time() - start_audit
    
    start_audit_verify = time.time()
    audit_result = router.audit_job_response(audit_proof, response)
    audit_verify_time = time.time() - start_audit_verify
    
    # Decode output
    output_text = provider.tokenizer.decode(response.output_tokens)
    
    # Calculate stats
    tokens_per_sec = len(response.output_tokens) / inference_time if inference_time > 0 else 0
    
    return {
        "model": model_path,
        "init_time": init_time,
        "inference_time": inference_time,
        "verify_time": verify_time,
        "audit_gen_time": audit_gen_time,
        "audit_verify_time": audit_verify_time,
        "total_time": init_time + inference_time + verify_time + audit_gen_time + audit_verify_time,
        "tokens": len(response.output_tokens),
        "tokens_per_sec": tokens_per_sec,
        "audit_passed": audit_result.passed,
        "output": output_text[:200],  # First 200 chars
        "transcript_root": response.transcript_root[:16],
    }


def main():
    print("🔬 Proof-of-Inference Model Comparison")
    print("=" * 60)
    
    # Test prompt
    prompt = {
        "messages": [
            {"role": "user", "content": "What is 2+2? Answer in one short sentence."}
        ]
    }
    
    models = [
        "mlx-community/Qwen3-0.6B-4bit",
        "mlx-community/Qwen3-4B-4bit",
    ]
    
    results = []
    
    for model_path in models:
        try:
            result = benchmark_model(model_path, prompt, max_tokens=30)
            results.append(result)
        except Exception as e:
            print(f"\n❌ Error testing {model_path}: {e}")
            continue
    
    # Print comparison table
    print("\n" + "=" * 60)
    print("📊 COMPARISON RESULTS")
    print("=" * 60)
    
    if not results:
        print("No results to compare")
        return
    
    # Header
    print(f"\n{'Metric':<25} {'0.6B-4bit':<20} {'4B-4bit':<20}")
    print("-" * 65)
    
    # Model size comparison
    print(f"{'Model':<25} {results[0]['model'].split('/')[-1]:<20} {results[1]['model'].split('/')[-1] if len(results) > 1 else 'N/A':<20}")
    
    # Timing comparisons
    metrics = [
        ("Init Time (s)", "init_time"),
        ("Inference Time (s)", "inference_time"),
        ("Tokens/sec", "tokens_per_sec"),
        ("Verify Time (ms)", "verify_time"),
        ("Audit Gen (ms)", "audit_gen_time"),
        ("Audit Verify (ms)", "audit_verify_time"),
        ("Total Time (s)", "total_time"),
        ("Tokens Generated", "tokens"),
        ("Audit Passed", "audit_passed"),
    ]
    
    for label, key in metrics:
        val0 = results[0].get(key, 0)
        val1 = results[1].get(key, 0) if len(results) > 1 else 0
        
        # Format based on metric
        if "Time" in label and "ms" in label:
            val0_str = f"{val0*1000:.2f}"
            val1_str = f"{val1*1000:.2f}" if len(results) > 1 else "N/A"
        elif "Time" in label or "total" in key.lower():
            val0_str = f"{val0:.3f}"
            val1_str = f"{val1:.3f}" if len(results) > 1 else "N/A"
        elif "tokens_per_sec" in key:
            val0_str = f"{val0:.1f}"
            val1_str = f"{val1:.1f}" if len(results) > 1 else "N/A"
        elif isinstance(val0, bool):
            val0_str = "✅" if val0 else "❌"
            val1_str = "✅" if val1 else "❌" if len(results) > 1 else "N/A"
        else:
            val0_str = str(val0)
            val1_str = str(val1) if len(results) > 1 else "N/A"
        
        print(f"{label:<25} {val0_str:<20} {val1_str:<20}")
    
    # Output samples
    print("\n" + "=" * 60)
    print("📝 OUTPUT SAMPLES")
    print("=" * 60)
    
    for i, result in enumerate(results):
        print(f"\n{result['model'].split('/')[-1]}:")
        print(f"  {result['output']}")
    
    # Winner analysis
    print("\n" + "=" * 60)
    print("🏆 ANALYSIS")
    print("=" * 60)
    
    if len(results) == 2:
        faster_model = 0 if results[0]['inference_time'] < results[1]['inference_time'] else 1
        faster_tps = 0 if results[0]['tokens_per_sec'] > results[1]['tokens_per_sec'] else 1
        
        print(f"\n⚡ Fastest Inference: {results[faster_model]['model'].split('/')[-1]}")
        print(f"   {results[faster_model]['inference_time']:.3f}s vs {results[1-faster_model]['inference_time']:.3f}s")
        print(f"   ({results[faster_model]['inference_time']/results[1-faster_model]['inference_time']*100:.1f}% of time)")
        
        print(f"\n🚀 Highest Throughput: {results[faster_tps]['model'].split('/')[-1]}")
        print(f"   {results[faster_tps]['tokens_per_sec']:.1f} tok/s vs {results[1-faster_tps]['tokens_per_sec']:.1f} tok/s")
        print(f"   ({results[faster_tps]['tokens_per_sec']/results[1-faster_tps]['tokens_per_sec']*100:.1f}% faster)")
        
        print(f"\n💾 Memory/Size Tradeoff:")
        print(f"   0.6B model: Smaller, faster, less capable")
        print(f"   4B model: Larger, slower, more capable")
        
        print(f"\n✅ Both models: Audit verification {'PASSED' if all(r['audit_passed'] for r in results) else 'FAILED'}")


if __name__ == "__main__":
    main()
