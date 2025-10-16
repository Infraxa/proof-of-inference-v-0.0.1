# Contributing to Proof-of-Inference

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/yourusername/proof-of-inference.git
   cd proof-of-inference
   ```

2. **Set up development environment**
   ```bash
   uv venv --python 3.12
   source .venv/bin/activate
   pip install mlx-lm mlx numpy huggingface-hub
   ```

3. **Run tests to verify setup**
   ```bash
   python demo.py
   python test_cheating.py
   ```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where possible
- Add docstrings to all functions and classes
- Keep functions focused and modular

## Testing

Before submitting a PR:

1. **Run all demos**
   ```bash
   python demo.py
   python compare_models.py
   python test_cheating.py
   ```

2. **Verify security tests pass**
   ```bash
   python test_cheating.py | grep "ALL SECURITY TESTS PASSED"
   ```

3. **Test with different models** (if applicable)

## Areas for Contribution

### High Priority
- [ ] Real VRF implementation (replace mock with elliptic curve VRF)
- [ ] ECDSA signatures (replace HMAC with proper crypto)
- [ ] Logits compression (reduce storage overhead)
- [ ] Batch inference support

### Medium Priority
- [ ] Support for GGUF models
- [ ] Multi-provider consensus
- [ ] TEE attestation integration
- [ ] Performance optimizations

### Documentation
- [ ] More examples
- [ ] API documentation
- [ ] Architecture diagrams
- [ ] Security analysis

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with clear commit messages
3. Add tests if applicable
4. Update documentation
5. Submit PR with description of changes
6. Respond to review feedback

## Questions?

Open an issue or discussion on GitHub!
