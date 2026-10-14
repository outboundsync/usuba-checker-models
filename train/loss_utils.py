"""v2 loss helpers: up-weight the verdict value tokens ("approve" / "changes_requested") in the assistant target.
Kept torch-free at import so the tokenizer-side code is unit-testable without a GPU (train/tests/test_loss_utils.py)."""
import re
VERDICT_KEY = re.compile(r'"verdict"\s*:\s*"')

def verdict_token_mask(tok, label_ids):
    """Indices (into label_ids, the assistant-token list) of the tokens that spell the verdict value.
    Maps characters to tokens by incremental decoding, so it works for any tokenizer/merge pattern.
    Returns [] when the target has no verdict (the row then trains unweighted)."""
    text = tok.decode(label_ids)
    m = VERDICT_KEY.search(text)
    if not m: return []
    v0 = m.end(); v1 = text.find('"', v0)
    if v1 <= v0: return []
    out, prev = [], 0
    for k in range(len(label_ids)):
        cur = len(tok.decode(label_ids[:k + 1]))
        if cur > v0 and prev < v1: out.append(k)    # token k covers chars [prev, cur)
        if prev >= v1: break
        prev = cur
    return out

def token_weights(tok, labels, verdict_weight):
    """Per-position weights aligned with labels (-100 = prompt). Assistant tokens weigh 1.0, verdict value tokens verdict_weight."""
    w = [0.0 if y == -100 else 1.0 for y in labels]
    if verdict_weight == 1.0: return w
    first = next((i for i, y in enumerate(labels) if y != -100), None)
    if first is None: return w
    for k in verdict_token_mask(tok, [y for y in labels[first:] if y != -100]): w[first + k] = float(verdict_weight)
    return w

def weighted_seq_loss(token_loss, token_w):
    """token_loss, token_w: [B, T] tensors (token_w = 0 on ignored positions). Per-sequence loss =
    sum(loss * w) / (number of assistant tokens): the verdict tokens count verdict_weight times, every other
    assistant token keeps its v1 weight, so the rest of the target is not diluted."""
    n = (token_w > 0).float().sum(1).clamp(min=1)
    return (token_loss * token_w).sum(1) / n
