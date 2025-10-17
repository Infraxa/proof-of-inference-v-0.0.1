pragma circom 2.0.0;

include "../../../node_modules/circomlib/circuits/poseidon.circom";

/*
 * Hash Preimage Proof
 * 
 * Proves: "I know preimage x such that hash(x) = h"
 * 
 * This is the simplest ZK circuit - just proving knowledge of
 * data that hashes to a public commitment.
 * 
 * For proof-of-inference, this demonstrates the concept:
 * - Provider: Knows logits L, computes hash(L) = H
 * - Router: Verifies proof that provider knows L without seeing L
 */

template HashPreimage(n) {
    // Public input: the hash we're proving preimage for
    signal input hash_output;
    
    // Private witness: the actual preimage (hidden from verifier)
    signal input preimage[n];
    
    // Compute hash of preimage using Poseidon
    component hasher = Poseidon(n);
    for (var i = 0; i < n; i++) {
        hasher.inputs[i] <== preimage[i];
    }
    
    // Constraint: computed hash must equal public hash
    hasher.out === hash_output;
}

// Instantiate with n=4 (4 field elements)
// This is small enough for quick testing
component main {public [hash_output]} = HashPreimage(4);
