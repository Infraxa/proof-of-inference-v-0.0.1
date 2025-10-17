pragma circom 2.0.0;

// Hash Preimage Proof (Simplified)
// Proves: "I know preimage x such that hash(x) = h"
// 
// For proof-of-inference, this demonstrates the concept:
// - Provider: Knows logits L, computes hash(L) = H
// - Router: Verifies proof that provider knows L without seeing L
// 
// Note: Using simple addition hash for demo (not cryptographically secure)
// Real implementation would use Poseidon or MiMC hash

template SimpleHash(n) {
    signal input inputs[n];
    signal output out;
    
    // Simple hash: just sum all inputs (for demo purposes)
    signal sums[n];
    sums[0] <== inputs[0];
    
    for (var i = 1; i < n; i++) {
        sums[i] <== sums[i-1] + inputs[i];
    }
    
    out <== sums[n-1];
}

template HashPreimage(n) {
    // Public input: the hash we're proving preimage for
    signal input hash_output;
    
    // Private witness: the actual preimage (hidden from verifier)
    signal input preimage[n];
    
    // Compute hash of preimage
    component hasher = SimpleHash(n);
    for (var i = 0; i < n; i++) {
        hasher.inputs[i] <== preimage[i];
    }
    
    // Constraint: computed hash must equal public hash
    hasher.out === hash_output;
}

// Instantiate with n=4 (4 field elements)
component main {public [hash_output]} = HashPreimage(4);
