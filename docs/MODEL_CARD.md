# Usuba (Omarchy plugin checker model) — model card (draft)

Base: Qwen 3.5 9B (Apache-2.0), bf16 LoRA. Task: review an Omarchy plugin (source + Checker report) and return a JSON verdict with findings.

## Training data provenance
**No proprietary-model outputs (Anthropic/Claude, OpenAI/GPT, Google/Gemini, xAI/Grok or any closed model) were used to train Usuba.**
Training data: real licensed plugins (see NOTICE); HANCORE findings from public GitHub review issues; scripted Checker reports; hardware-verified
Omarchy 4.0.4 labels; real upstream fix commits graded by the Checker; and review text written only by the open-weights teacher
**Qwen3.5-397B-A17B (Apache-2.0)** — https://huggingface.co/Qwen/Qwen3.5-397B-A17B/blob/main/LICENSE — filtered against the grader labels.
Teacher license: Apache-2.0 (no restriction on training other models on its outputs). Proprietary models appear only as evaluation baselines.
Full method: `train/v2/distill/METHODS.md`, `train/v2/distill/TEACHER.md`.
