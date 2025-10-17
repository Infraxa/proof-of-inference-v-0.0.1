# ZK-SNARK Proof-of-Inference

**Status**: 🚧 Proof-of-Concept

## Overview

Zero-knowledge succinct non-interactive arguments of knowledge for proving correct inference execution without revealing intermediate states.

## Why ZK-SNARKs?

**Current system (Merkle + Audit):**
- ❌ Interactive (requires back-and-forth)
- ❌ Reveals logits during audit
- ❌ Probabilistic (only checks 10% of steps)

**ZK-SNARK system:**
- ✅ Non-interactive (one-shot verification)
- ✅ Zero-knowledge (hides intermediate computations)
- ✅ Deterministic (cryptographic guarantee)
- ✅ Succinct (constant-size proofs ~200-500 bytes)

## Implementation Phases

### Phase 1: Hash Preimage (Warmup) ✅
**Goal**: Prove knowledge of data that hashes to a commitment

```circom
// Prove: "I know x such that hash(x) = h"
template HashPreimage(n) {
    signal input hash_output;     // Public
    signal input preimage[n];     // Private witness
    
    component hasher = Poseidon(n);
    for (var i = 0; i < n; i++) {
        hasher.inputs[i] <== preimage[i];
    }
    
    hasher.out === hash_output;
}
```

**Status**: Circuit implemented, ready to test

### Phase 2: Logits Commitment (Current Focus) 🚧
**Goal**: Prove logits hash to committed value

```circom
// Prove: "I have logits L such that hash(L) = H"
template LogitsCommitment(vocab_size) {
    signal input logits_hash;           // Public
    signal input logits[vocab_size];    // Private witness
    
    component hasher = Poseidon(vocab_size);
    for (var i = 0; i < vocab_size; i++) {
        hasher.inputs[i] <== logits[i];
    }
    
    hasher.out === logits_hash;
}
```

**Challenge**: Vocab size is huge (32k-100k tokens)
**Solution**: Use Merkle tree + prove single leaf

### Phase 3: Quantized Matrix Multiply (Future)
**Goal**: Prove int8 matrix multiplication

```circom
template QuantizedMatMul(m, n, k) {
    signal input A[m][k];     // Input (int8)
    signal input B[k][n];     // Weights (int8)
    signal input scale;       // Quantization scale
    signal output C[m][n];    // Output
    
    // Prove: C = (A @ B) / scale
}
```

**Challenge**: Large circuits (millions of constraints)

### Phase 4: Single Inference Step (Advanced)
**Goal**: Prove one transformer layer forward pass

**Challenge**: Extremely large circuits (billions of constraints)

## Technology Stack

### Circuit Language
- **circom**: Most popular, good documentation
- **snarkjs**: JavaScript SNARK toolkit for proving/verification

### Proof System
- **Groth16**: Fast verification, requires trusted setup
- **PLONK**: Universal setup, slightly slower (better for PoC)

### Python Integration
- Use `subprocess` to call snarkjs
- Or use `py_ecc` for pure Python (limited)

## Quick Start

### Prerequisites
```bash
# Install Node.js and circom
brew install node
npm install -g snarkjs
npm install -g circom

# Or use Docker
docker pull iden3/circom
```

### Run Phase 1 Demo
```bash
cd variants/zk_snark
python demo_hash_preimage.py
```

## Performance Expectations

| Phase | Circuit Size | Proving Time | Verification Time | Proof Size |
|-------|--------------|--------------|-------------------|------------|
| Hash Preimage | ~1K constraints | ~100ms | <10ms | 200 bytes |
| Logits Commitment | ~10K constraints | ~1s | <10ms | 200 bytes |
| Matrix Multiply | ~1M constraints | ~10s | <10ms | 200 bytes |
| Full Step | ~1B constraints | ~1000s | <10ms | 200 bytes |

**Key insight**: Verification is always fast (constant time), proving scales with circuit complexity.

## Comparison with Current System

| Metric | Current (Merkle) | ZK-SNARK |
|--------|------------------|----------|
| Verification | 3 steps × inference | ~10ms |
| Proof size | 3 × logits | 200 bytes |
| Interactive | Yes | No |
| Privacy | Reveals logits | Zero-knowledge |
| Maturity | Production | Research |

## Limitations

### Current PoC
- ❌ Only proves hash preimage (not actual inference)
- ❌ Requires trusted setup (Groth16)
- ❌ Proving time >> inference time
- ❌ Circuit complexity limits model size

### For Production
Would need:
- [ ] Recursive proofs (prove full sequence)
- [ ] Optimized circuits (reduce constraints)
- [ ] Hardware acceleration (GPU proving)
- [ ] Universal setup (PLONK/Halo2)

## Files

```
variants/zk_snark/
├── circuits/
│   ├── hash_preimage.circom       # Phase 1: Simple hash proof
│   ├── logits_commitment.circom   # Phase 2: Logits hash proof
│   └── build/                     # Compiled circuits
├── demo_hash_preimage.py          # Phase 1 demo
├── zk_provider.py                 # Provider that generates ZK proofs
├── zk_router.py                   # Router that verifies ZK proofs
├── setup.sh                       # Setup trusted ceremony
└── README.md                      # This file
```

## Next Steps

1. ✅ Implement Phase 1 (hash preimage)
2. 🚧 Test with real data from MLX inference
3. 📊 Benchmark proving vs verification time
4. 📝 Document feasibility for Phase 2+

## References

- **circom docs**: https://docs.circom.io/
- **snarkjs**: https://github.com/iden3/snarkjs
- **ZK learning**: https://zk-learning.org/
- **Groth16 paper**: https://eprint.iacr.org/2016/260.pdf
