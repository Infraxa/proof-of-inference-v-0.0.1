# Running with Real MLX Model

This guide shows how to run the Proof-of-Inference demo with a real MLX model (Qwen3-4B-4bit).

## Prerequisites

- **macOS** with Apple Silicon (M1, M2, M3, M4)
- **Python 3.9, 3.10, 3.11, or 3.12** (NOT 3.13)
- At least **8GB free disk space** (for model download)
- At least **8GB RAM**

## Installation Steps

### 1. Check Your Python Version

```bash
python --version
```

You should see something like `Python 3.12.x`. If you see `3.13`, you need to install an older version.

### 2. Create a Virtual Environment (Recommended)

```bash
# Using Python 3.12 (or 3.11, 3.10, 3.9)
python3.12 -m venv venv
source venv/bin/activate
```

### 3. Install MLX and Dependencies

```bash
pip install --upgrade pip
pip install mlx-lm mlx numpy huggingface-hub
```

This will install:
- `mlx` - Apple's ML framework
- `mlx-lm` - Language model utilities for MLX
- `numpy` - For numerical operations
- `huggingface-hub` - For model downloading

### 4. Verify Installation

```bash
python -c "import mlx_lm; print('MLX-LM version:', mlx_lm.__version__)"
```

You should see: `MLX-LM version: 0.xx.x`

## Running the Demo

### First Run (Downloads Model)

```bash
python demo.py
```

**First run will:**
1. Download Qwen3-4B-4bit from Hugging Face (~2.5GB)
2. Cache it locally at `~/.cache/huggingface/hub/`
3. Run inference with cryptographic verification

**Expected output:**
```
✅ MLX-LM available - using real inference

1. Initializing Provider...
   Model will be downloaded from Hugging Face if not cached...
Loading model: mlx-community/Qwen3-4B-4bit
Fetching 10 files: 100%|████████████| 10/10 [00:45<00:00,  4.52s/it]
Model hash: <hash>

2. Initializing Router...

3. Creating Job...
Job created: <uuid>

4. Provider Processing Job...
   Processing time: 2.34s
   Output tokens: 15
   Transcript root: <merkle_root>...

5. Router Verifying Response...
✅ Response verification passed

6. Audit Decision: YES
7. Creating Audit Challenge...
Challenge steps: [2, 8, 12]

8. Provider Generating Audit Proof...
9. Router Performing Audit...
✅ Audit PASSED - Provider verified!

10. Final Output:
Response: The answer is 4. Two plus two equals four.

🎉 Demo Complete!
```

### Subsequent Runs

After the first run, the model is cached and loads instantly:

```bash
python demo.py
```

## Troubleshooting

### "No module named 'mlx_lm'"

**Solution:** Install MLX:
```bash
pip install mlx-lm mlx
```

### "MLX requires Python 3.9-3.12"

**Solution:** You're using Python 3.13. Create a venv with Python 3.12:
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install mlx-lm mlx numpy
```

### "No wheels found for mlx"

**Possible causes:**
1. **Not on Apple Silicon** - MLX only works on M1/M2/M3/M4 Macs
2. **Wrong Python version** - Use 3.9-3.12
3. **Free-threaded Python** - Don't use `python3.13t`

**Solution:** Use standard Python 3.12 on Apple Silicon Mac.

### Model Download is Slow

The model is 2.5GB. On slow connections:
```bash
# Pre-download the model
python -c "from mlx_lm import load; load('mlx-community/Qwen3-4B-4bit')"
```

### Out of Memory

Qwen3-4B-4bit needs ~4GB RAM. If you run out:
- Close other applications
- Use a smaller model: `mlx-community/Qwen3-1.5B-4bit`

## Using Different Models

Edit `demo.py` line 23:

```python
# Smaller model (1.5B parameters)
model_path = "mlx-community/Qwen3-1.5B-4bit"

# Larger model (8B parameters, needs 16GB RAM)
model_path = "mlx-community/Qwen3-8B-4bit"

# Other models
model_path = "mlx-community/Llama-3.2-3B-Instruct-4bit"
```

## Performance Benchmarks

On M3 Max:
- **Model Load:** ~2s (cached)
- **Inference:** ~50 tokens/sec
- **Transcript Overhead:** ~5-10%
- **Audit Verification:** <1s per step

## Next Steps

1. **Modify the prompt** in `demo.py` line 35
2. **Adjust generation parameters** (temperature, max_tokens)
3. **Implement custom audit logic** in `router.py`
4. **Add real cryptographic signing** (replace HMAC with ECDSA)

## Resources

- [MLX Documentation](https://ml-explore.github.io/mlx/)
- [MLX-LM GitHub](https://github.com/ml-explore/mlx-lm)
- [Qwen3 Model Card](https://huggingface.co/mlx-community/Qwen3-4B-4bit)
- [Proof-of-Inference Design](../README.md)
