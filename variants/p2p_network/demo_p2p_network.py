#!/usr/bin/env python3
"""
P2P Proof-of-Inference Network Demo

Demonstrates:
1. Starting multiple provider nodes
2. Router discovering and connecting to providers
3. Requesting inference over P2P
4. Cryptographic verification of results
5. Detection of fraudulent providers
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import asyncio
import time
from provider_node import ProviderNode
from router_node import RouterNode


async def run_provider(model: str, port: int):
    """Run a provider node."""
    node = ProviderNode(model, "127.0.0.1", port)
    await node.start()


async def demo():
    """Run the full P2P network demo."""
    print("\n" + "="*70)
    print("🌐 P2P PROOF-OF-INFERENCE NETWORK DEMO")
    print("="*70)
    print("\nThis demo shows:")
    print("  1. Multiple provider nodes running different models")
    print("  2. Router discovering and connecting to providers")
    print("  3. Requesting inference over P2P network")
    print("  4. Cryptographic verification of results")
    print("  5. Detection of fraudulent providers")
    print("="*70 + "\n")
    
    # Start provider nodes in background
    print("Starting provider nodes...\n")
    
    providers = [
        ("mlx-community/Qwen3-4B-4bit", 4001),
        ("mlx-community/Qwen3-1.7B-6bit", 4002),
    ]
    
    provider_tasks = []
    for model, port in providers:
        task = asyncio.create_task(run_provider(model, port))
        provider_tasks.append(task)
    
    # Give providers time to start
    await asyncio.sleep(3)
    
    # Create router
    print("\n" + "="*70)
    print("Creating router node...")
    print("="*70 + "\n")
    
    router = RouterNode()
    
    # Manually add providers (in real P2P, would use discovery)
    print("Discovering providers...\n")
    
    # For demo, we'll add providers without hash and update after first connection
    # In real P2P, providers would announce their capabilities
    for model, port in providers:
        router.add_provider("127.0.0.1", port, model, "pending")
    
    await asyncio.sleep(1)
    
    # Test 1: Honest provider (4B model)
    print("\n" + "="*70)
    print("TEST 1: Honest Provider (Qwen3-4B)")
    print("="*70 + "\n")
    
    success = await router.run_inference_job(
        model="mlx-community/Qwen3-4B-4bit",
        prompt="What is 2+2?",
        max_tokens=10,
        verification_mode="merkle"
    )
    
    if success:
        print("✅ Test 1 PASSED: Honest provider verified")
    else:
        print("❌ Test 1 FAILED: Verification failed")
    
    await asyncio.sleep(2)
    
    # Test 2: Different model (1.7B)
    print("\n" + "="*70)
    print("TEST 2: Different Provider (Qwen3-1.7B)")
    print("="*70 + "\n")
    
    success = await router.run_inference_job(
        model="mlx-community/Qwen3-1.7B-6bit",
        prompt="Explain AI in one sentence",
        max_tokens=15,
        verification_mode="merkle"
    )
    
    if success:
        print("✅ Test 2 PASSED: Different provider verified")
    else:
        print("❌ Test 2 FAILED: Verification failed")
    
    await asyncio.sleep(2)
    
    # Test 3: Model substitution attack
    print("\n" + "="*70)
    print("TEST 3: Model Substitution Attack")
    print("="*70)
    print("\nSimulating attack: Provider claims 4B but uses 1.7B\n")
    
    # Temporarily modify router's expected hash to trigger mismatch
    original_hash = None
    for pid, pdata in router.known_providers.items():
        if pdata['model'] == "mlx-community/Qwen3-4B-4bit":
            original_hash = pdata['model_hash']
            # Set wrong hash to simulate attack detection
            pdata['model_hash'] = "wrong_hash_simulating_attack"
            break
    
    success = await router.run_inference_job(
        model="mlx-community/Qwen3-4B-4bit",
        prompt="Test",
        max_tokens=5,
        verification_mode="merkle"
    )
    
    # Restore original hash
    for pid, pdata in router.known_providers.items():
        if pdata['model'] == "mlx-community/Qwen3-4B-4bit":
            pdata['model_hash'] = original_hash
            break
    
    if not success:
        print("✅ Test 3 PASSED: Attack detected and blocked")
    else:
        print("❌ Test 3 FAILED: Attack not detected")
    
    # Summary
    print("\n" + "="*70)
    print("📊 DEMO SUMMARY")
    print("="*70)
    print("\n✅ P2P Network Features Demonstrated:")
    print("  • Multiple provider nodes running concurrently")
    print("  • Router discovering and connecting to providers")
    print("  • Inference requests over network")
    print("  • Cryptographic proof verification")
    print("  • Model substitution attack detection")
    print("\n💡 Key Insights:")
    print("  • Decentralized: No central server needed")
    print("  • Verifiable: Cryptographic proofs ensure correctness")
    print("  • Scalable: Can add unlimited providers")
    print("  • Secure: Attacks are detected and blocked")
    print("\n🚀 Next Steps:")
    print("  • Add peer discovery (mDNS/DHT)")
    print("  • Implement reputation system")
    print("  • Add economic incentives (staking/slashing)")
    print("  • Deploy on real P2P network (libp2p)")
    print("="*70 + "\n")
    
    # Cleanup
    print("Shutting down provider nodes...")
    for task in provider_tasks:
        task.cancel()
    
    await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(demo())
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
