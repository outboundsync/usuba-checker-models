"""CPU unit tests for the verdict-token loss weight. Run: python -m pytest train/tests -q (needs torch + transformers; the
Qwen3.5-9B tokenizer files only, no weights)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import torch
from transformers import AutoTokenizer
import loss_utils as L, prompt
TOK = AutoTokenizer.from_pretrained(os.environ.get("TEST_TOKENIZER", "Qwen/Qwen3.5-9B"))

def encode(target):
    msgs = prompt.messages("### manifest.json\n```\n{}\n```", [], target)
    p = TOK.apply_chat_template(msgs[:-1], tokenize=True, add_generation_prompt=True, enable_thinking=False)
    f = TOK.apply_chat_template(msgs, tokenize=True, add_generation_prompt=False, enable_thinking=False)
    if hasattr(p, "input_ids"): p, f = p["input_ids"], f["input_ids"]
    return f, [-100] * len(p) + f[len(p):]

def test_verdict_tokens_spell_the_verdict():
    for v in ("approve", "changes_requested"):
        ids, lab = encode(dict(verdict=v, load=None, findings=[]))
        w = L.token_weights(TOK, lab, 5.0)
        hot = [ids[i] for i, x in enumerate(w) if x == 5.0]
        assert hot, v
        assert TOK.decode(hot).strip().strip('"') == v, (v, TOK.decode(hot))

def test_weights_only_on_assistant_and_count():
    ids, lab = encode(dict(verdict="approve", load="works", findings=[dict(category="other", severity="warning", file=None, finding="approve this? no")]))
    w = L.token_weights(TOK, lab, 5.0)
    assert all(x == 0.0 for x, y in zip(w, lab) if y == -100)
    assert sum(1 for x in w if x == 5.0) == len(TOK.encode("approve", add_special_tokens=False)) or sum(1 for x in w if x == 5.0) <= 3
    # only the verdict value, not the word "approve" inside a finding
    first5 = [i for i, x in enumerate(w) if x == 5.0]
    assert max(first5) - min(first5) < 4

def test_weight_one_is_v1_behavior():
    ids, lab = encode(dict(verdict="changes_requested", load=None, findings=[]))
    assert L.token_weights(TOK, lab, 1.0) == [0.0 if y == -100 else 1.0 for y in lab]

def test_weighted_seq_loss_math():
    tl = torch.tensor([[1.0, 2.0, 3.0, 4.0]]); w = torch.tensor([[0.0, 5.0, 1.0, 1.0]])
    # (2*5 + 3 + 4) / 3 assistant tokens
    assert torch.allclose(L.weighted_seq_loss(tl, w), torch.tensor([17.0 / 3]))
    w1 = torch.tensor([[0.0, 1.0, 1.0, 1.0]])
    assert torch.allclose(L.weighted_seq_loss(tl, w1), torch.tensor([3.0]))   # == v1 masked mean

def test_gradient_on_verdict_is_5x():
    logits = torch.zeros(1, 3, 7, requires_grad=True); lab = torch.tensor([[2, 3, 4]])
    tl = torch.nn.functional.cross_entropy(logits.view(-1, 7), lab.view(-1), reduction="none").view(1, 3)
    L.weighted_seq_loss(tl, torch.tensor([[5.0, 1.0, 1.0]])).sum().backward()
    g = logits.grad.abs().sum(-1)[0]
    assert torch.allclose(g[0] / g[1], torch.tensor(5.0))
