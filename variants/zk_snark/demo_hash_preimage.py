#!/usr/bin/env python3
"""
ZK-SNARK Demo: Hash Preimage Proof

Demonstrates the simplest ZK circuit for proof-of-inference concept.

Flow:
1. Provider has secret data (preimage)
2. Provider computes hash and commits to it
3. Provider generates ZK proof: "I know preimage"
4. Router verifies proof without seeing preimage

This is analogous to:
- Preimage = logits from inference
- Hash = commitment in Merkle tree
- Proof = ZK proof of correct inference
"""

import subprocess
import json
import os
import sys

# Check if circom and snarkjs are installed
def check_dependencies():
    """Check if required tools are installed."""
    print("Checking dependencies...")
    
    try:
        result = subprocess.run(['circom', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"  ✅ circom: {result.stdout.strip()}")
        else:
            print("  ❌ circom not found")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("  ❌ circom not found")
        print("\nInstall with:")
        print("  npm install -g circom")
        return False
    
    try:
        result = subprocess.run(['snarkjs', '--version'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"  ✅ snarkjs: {result.stdout.strip()}")
        else:
            print("  ❌ snarkjs not found")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("  ❌ snarkjs not found")
        print("\nInstall with:")
        print("  npm install -g snarkjs")
        return False
    
    return True


def compile_circuit():
    """Compile the circom circuit."""
    print("\n" + "="*70)
    print("STEP 1: Compiling Circuit")
    print("="*70)
    
    circuit_path = "circuits/hash_preimage.circom"
    build_dir = "circuits/build"
    
    os.makedirs(build_dir, exist_ok=True)
    
    print(f"\nCompiling {circuit_path}...")
    
    # Compile circuit to R1CS
    result = subprocess.run([
        'circom',
        circuit_path,
        '--r1cs',
        '--wasm',
        '--sym',
        '-o', build_dir
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Compilation failed:")
        print(result.stderr)
        return False
    
    print("✅ Circuit compiled successfully")
    print(f"   Output: {build_dir}/hash_preimage.r1cs")
    
    # Get circuit info
    result = subprocess.run([
        'snarkjs', 'r1cs', 'info',
        f'{build_dir}/hash_preimage.r1cs'
    ], capture_output=True, text=True)
    
    print("\nCircuit Info:")
    print(result.stdout)
    
    return True


def setup_ceremony():
    """Perform trusted setup ceremony."""
    print("\n" + "="*70)
    print("STEP 2: Trusted Setup Ceremony")
    print("="*70)
    
    build_dir = "circuits/build"
    
    print("\nGenerating Powers of Tau...")
    # Phase 1: Powers of Tau (universal, can be reused)
    result = subprocess.run([
        'snarkjs', 'powersoftau', 'new', 'bn128', '12',
        f'{build_dir}/pot12_0000.ptau', '-v'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Powers of Tau failed:")
        print(result.stderr)
        return False
    
    print("✅ Powers of Tau generated")
    
    # Contribute to ceremony (in production, multiple parties contribute)
    print("\nContributing to ceremony...")
    result = subprocess.run([
        'snarkjs', 'powersoftau', 'contribute',
        f'{build_dir}/pot12_0000.ptau',
        f'{build_dir}/pot12_0001.ptau',
        '--name="First contribution"', '-v'
    ], capture_output=True, text=True, input="random entropy\n")
    
    if result.returncode != 0:
        print(f"❌ Contribution failed:")
        print(result.stderr)
        return False
    
    print("✅ Contribution added")
    
    # Phase 2: Circuit-specific setup
    print("\nPreparing Phase 2...")
    result = subprocess.run([
        'snarkjs', 'powersoftau', 'prepare', 'phase2',
        f'{build_dir}/pot12_0001.ptau',
        f'{build_dir}/pot12_final.ptau', '-v'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Phase 2 prep failed:")
        print(result.stderr)
        return False
    
    print("✅ Phase 2 ready")
    
    # Generate proving and verification keys
    print("\nGenerating zkey...")
    result = subprocess.run([
        'snarkjs', 'groth16', 'setup',
        f'{build_dir}/hash_preimage.r1cs',
        f'{build_dir}/pot12_final.ptau',
        f'{build_dir}/hash_preimage_0000.zkey'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ zkey generation failed:")
        print(result.stderr)
        return False
    
    print("✅ Proving key generated")
    
    # Export verification key
    print("\nExporting verification key...")
    result = subprocess.run([
        'snarkjs', 'zkey', 'export', 'verificationkey',
        f'{build_dir}/hash_preimage_0000.zkey',
        f'{build_dir}/verification_key.json'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Verification key export failed:")
        print(result.stderr)
        return False
    
    print("✅ Verification key exported")
    
    return True


def generate_proof():
    """Generate a ZK proof."""
    print("\n" + "="*70)
    print("STEP 3: Generating ZK Proof (Provider)")
    print("="*70)
    
    build_dir = "circuits/build"
    
    # Provider's secret: preimage (4 field elements)
    preimage = [1, 2, 3, 4]
    
    print(f"\nProvider's secret preimage: {preimage}")
    print("(This will NOT be revealed to the verifier)")
    
    # Compute hash (we'll use a mock hash for demo)
    # In real implementation, this would be Poseidon hash
    hash_output = 12345  # Mock hash value
    
    print(f"Public hash commitment: {hash_output}")
    
    # Create input JSON
    input_data = {
        "hash_output": str(hash_output),
        "preimage": [str(x) for x in preimage]
    }
    
    with open(f'{build_dir}/input.json', 'w') as f:
        json.dump(input_data, f)
    
    print("\nGenerating witness...")
    result = subprocess.run([
        'node',
        f'{build_dir}/hash_preimage_js/generate_witness.js',
        f'{build_dir}/hash_preimage_js/hash_preimage.wasm',
        f'{build_dir}/input.json',
        f'{build_dir}/witness.wtns'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Witness generation failed:")
        print(result.stderr)
        return False
    
    print("✅ Witness generated")
    
    # Generate proof
    print("\nGenerating ZK proof...")
    print("(This is the computationally expensive part)")
    
    result = subprocess.run([
        'snarkjs', 'groth16', 'prove',
        f'{build_dir}/hash_preimage_0000.zkey',
        f'{build_dir}/witness.wtns',
        f'{build_dir}/proof.json',
        f'{build_dir}/public.json'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Proof generation failed:")
        print(result.stderr)
        return False
    
    print("✅ ZK Proof generated!")
    
    # Show proof size
    proof_size = os.path.getsize(f'{build_dir}/proof.json')
    print(f"\nProof size: {proof_size} bytes")
    print("(Constant size regardless of preimage size!)")
    
    return True


def verify_proof():
    """Verify the ZK proof."""
    print("\n" + "="*70)
    print("STEP 4: Verifying ZK Proof (Router)")
    print("="*70)
    
    build_dir = "circuits/build"
    
    print("\nRouter verifying proof...")
    print("(Router does NOT see the preimage)")
    print("(Router only sees: hash commitment + proof)")
    
    result = subprocess.run([
        'snarkjs', 'groth16', 'verify',
        f'{build_dir}/verification_key.json',
        f'{build_dir}/public.json',
        f'{build_dir}/proof.json'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Verification failed:")
        print(result.stderr)
        return False
    
    if "OK" in result.stdout:
        print("✅ Proof VERIFIED!")
        print("\n🎉 Router is convinced that provider knows the preimage")
        print("   WITHOUT ever seeing the preimage itself!")
        return True
    else:
        print("❌ Proof verification failed")
        print(result.stdout)
        return False


def main():
    print("\n" + "="*70)
    print("🔐 ZK-SNARK PROOF-OF-INFERENCE DEMO")
    print("="*70)
    print("\nPhase 1: Hash Preimage Proof")
    print("\nThis demonstrates the core ZK concept:")
    print("  • Provider knows secret data (preimage/logits)")
    print("  • Provider commits to hash of data")
    print("  • Provider generates ZK proof")
    print("  • Router verifies WITHOUT seeing secret data")
    print("="*70)
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Missing dependencies. Please install circom and snarkjs.")
        sys.exit(1)
    
    # Change to zk_snark directory
    os.chdir(os.path.dirname(__file__))
    
    # Run the demo
    if not compile_circuit():
        sys.exit(1)
    
    if not setup_ceremony():
        sys.exit(1)
    
    if not generate_proof():
        sys.exit(1)
    
    if not verify_proof():
        sys.exit(1)
    
    # Summary
    print("\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)
    print("\n✅ ZK-SNARK proof-of-concept successful!")
    print("\nKey Properties Demonstrated:")
    print("  • Zero-knowledge: Verifier never sees preimage")
    print("  • Succinct: Proof size is constant (~200 bytes)")
    print("  • Non-interactive: One-shot verification")
    print("  • Sound: Cannot fake proofs")
    print("\nNext Steps:")
    print("  • Phase 2: Prove logits commitment")
    print("  • Phase 3: Prove quantized matrix multiply")
    print("  • Phase 4: Prove full inference step")
    print("\nChallenges:")
    print("  • Circuit complexity grows with model size")
    print("  • Proving time >> inference time")
    print("  • Requires trusted setup (or use PLONK)")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
