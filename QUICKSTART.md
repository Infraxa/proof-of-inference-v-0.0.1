# Quick Start Guide

Get up and running with Proof-of-Inference in 5 minutes.

## Prerequisites

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.12 (recommended)

## Installation (2 minutes)

```bash
# 1. Create virtual environment
uv venv --python 3.12
source .venv/bin/activate

# 2. Install dependencies
pip install mlx-lm mlx numpy huggingface-hub
```

## Run Your First Demo (3 minutes)

```bash
# Basic demo - shows complete proof-of-inference flow
python demo.py
```

**What you'll see:**
1. Model loading (Qwen3-4B-4bit, ~2.5GB download on first run)
2. Job creation with cryptographic nonce
3. Inference with transcript generation
4. Response verification
5. Probabilistic audit with Merkle proofs
6. ✅ Audit passed!

## Try More Examples

### Compare Model Performance
```bash
python compare_models.py
```
Compares 0.6B vs 4B models for speed and throughput.

### Test Security
```bash
python test_cheating.py
```
Demonstrates how the system catches cheating providers.

## Next Steps

- Read [README.md](README.md) for full documentation
- Check [SETUP_MLX.md](SETUP_MLX.md) for troubleshooting
- See [CONTRIBUTING.md](CONTRIBUTING.md) to contribute

## Common Issues

### "MLX not available"
- Ensure you're on Apple Silicon Mac
- Use Python 3.9-3.12 (not 3.13)
- See SETUP_MLX.md for details

### Model download slow
- First download takes ~5 minutes (2.5GB)
- Subsequent runs use cached model (instant)

### Audit failures
- Normal with temperature > 0 (non-deterministic)
- System caches real logits to prevent this

## Understanding the Output

```
✅ Response verification passed  → Signature & hash valid
✅ Audit PASSED                  → Merkle proofs verified
```

Both checks must pass for a valid proof-of-inference!

---

**Ready to dive deeper?** Check out the [full README](README.md)!
