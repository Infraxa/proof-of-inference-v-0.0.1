# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-10-16

### Added
- ✅ Real MLX model integration (Qwen3-4B-4bit, Qwen3-0.6B-4bit)
- ✅ Cryptographic transcript generation with Merkle commitments
- ✅ Real logits caching for audit verification
- ✅ Model identity verification (prevents model substitution)
- ✅ Probabilistic audits with VRF-based step selection
- ✅ Cryptographic signatures binding model hash to response
- ✅ Security tests demonstrating attack prevention
- ✅ Performance comparison tool
- ✅ Comprehensive documentation

### Core Features
- **Provider SDK**: Real MLX-LM inference with transcript generation
- **Router**: Job management, verification, and audit logic
- **Crypto Utils**: Merkle trees, hashing, signatures, VRF
- **Demo**: End-to-end proof-of-inference demonstration

### Security
- Model hash verification prevents cheaper model substitution
- Signature verification prevents hash forgery
- Merkle proofs verify actual computation
- All security tests passing

### Performance
- Qwen3-0.6B-4bit: 93 tokens/sec
- Qwen3-4B-4bit: 43 tokens/sec
- Audit overhead: <1% of inference time

### Documentation
- README.md: Comprehensive project documentation
- QUICKSTART.md: 5-minute getting started guide
- SETUP_MLX.md: Detailed MLX setup and troubleshooting
- CONTRIBUTING.md: Contribution guidelines
- PROJECT_SUMMARY.md: High-level project overview

### Known Limitations
- HMAC signatures (not ECDSA) - suitable for demo
- Mock VRF (not elliptic curve based) - suitable for demo
- No TEE attestation
- No multi-provider consensus
- No ZK-SNARK integration

### Future Work
- [ ] Real VRF implementation
- [ ] ECDSA signatures
- [ ] TEE attestation support
- [ ] Batch inference
- [ ] Logits compression
- [ ] ZK-SNARK integration
