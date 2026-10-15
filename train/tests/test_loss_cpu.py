"""A4: CPU-only loss tests (no transformers/tokenizer download): verdict token mask with a char-level fake tokenizer, and the weighting actually changes gradients."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
torch = pytest.importorskip("torch")
import loss_utils as L


class CharTok:
    def decode(self, ids): return "".join(chr(i) for i in ids)


def test_verdict_tokens_found_and_weighted():
    txt = '{"verdict": "approve", "load": "works", "findings": []}'; ids = [ord(c) for c in txt]
    m = L.verdict_token_mask(CharTok(), ids); assert "".join(txt[i] for i in m) == "approve"
    labels = [-100] * 5 + ids; w = L.token_weights(CharTok(), labels, 4.0)
    assert w[:5] == [0.0] * 5 and sorted(set(w)) == [0.0, 1.0, 4.0] and sum(x == 4.0 for x in w) == len("approve")
    assert L.token_weights(CharTok(), labels, 1.0).count(1.0) == len(ids)


def test_weight_changes_gradient_even_at_batch_one():
    logits = torch.randn(1, 6, 5, requires_grad=True); y = torch.randint(0, 5, (1, 6))
    tl = torch.nn.functional.cross_entropy(logits.transpose(1, 2), y, reduction="none")
    def g(w):
        logits.grad = None; L.weighted_seq_loss(tl if False else torch.nn.functional.cross_entropy(logits.transpose(1, 2), y, reduction="none"), w).sum().backward(); return logits.grad.clone()
    g1 = g(torch.ones(1, 6)); w = torch.ones(1, 6); w[0, 2] = 5.0; g2 = g(w)
    assert not torch.allclose(g1, g2) and g2[0, 2].abs().sum() > g1[0, 2].abs().sum()
