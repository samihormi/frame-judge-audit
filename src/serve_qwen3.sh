#!/usr/bin/env bash
# Serve Qwen/Qwen3-32B (BF16, TP=2) with the installed vLLM's qwen3 reasoning parser.
# Runtime: base conda env (python 3.13, torch 2.10.0+cu128, vllm 0.19.0), driver 535.247.01.
set -euo pipefail
export HF_HOME=${HF_HOME:-$HOME/.cache/huggingface}
export VLLM_LOGGING_LEVEL=INFO
export CUDA_VISIBLE_DEVICES=0,1
MODEL=Qwen/Qwen3-32B
REV=9216db5781bf21249d130ec9da846c4624c16137
PORT=${PORT:-8077}
LOG=${LOG_DIR:-logs}/vllm_server.log
mkdir -p "$(dirname "$LOG")"
exec ${VLLM:-vllm} serve "$MODEL" \
  --revision "$REV" \
  --served-model-name qwen3-32b \
  --dtype bfloat16 \
  --tensor-parallel-size 2 \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.90 \
  --reasoning-parser qwen3 \
  --max-num-seqs 32 \
  --port "$PORT" >> "$LOG" 2>&1
