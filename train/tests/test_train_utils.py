import gzip, json, os, sys
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import train_utils as U


def test_weighted_loss_gradient_is_proportional_to_weight():
    torch = pytest.importorskip("torch")
    for w in (1.0, 2.0, 0.3):
        theta = torch.tensor([0.7], requires_grad=True)
        per = (theta * torch.tensor([3.0])).sum().reshape(1)        # one example, per_device_batch=1
        U.weighted_micro_loss(per, torch.tensor([w]), 16).backward()
        g = theta.grad.item()
        assert g == pytest.approx(w * 3.0 / 16)
    # the buggy formula would have returned the same gradient for every w
    theta = torch.tensor([0.7], requires_grad=True); per = (theta * 3.0).reshape(1); w = torch.tensor([2.0])
    ((per * w).sum() / w.sum()).backward(); assert theta.grad.item() == pytest.approx(3.0)


def test_weighted_loss_batch_of_two():
    torch = pytest.importorskip("torch")
    per = torch.tensor([1.0, 4.0]); w = torch.tensor([2.0, 1.0])
    assert U.weighted_micro_loss(per, w, 8).item() == pytest.approx((2 * 1 + 4) / (2 * 8))


def test_schedule_exact_and_fails_without_midrun_eval():
    s = U.schedule(896, 1, 16, 2, 0.03, eval_every_epochs=0.5)
    assert s["steps_per_epoch"] == 56 and s["total_steps"] == 112 and s["eval_every_steps"] == 28 and s["eval_steps"] == [28, 56, 84]
    with pytest.raises(SystemExit): U.schedule(896, 1, 16, 2, 0.03, eval_every_steps=145)     # the old r4 config: no mid-run eval
    s = U.schedule(100, 1, 16, 2, 0.03, eval_every_steps=3)
    assert s["total_steps"] == 14 and s["last_window"] == 4             # 100 micro/epoch -> 7 steps, last window of 4


def test_window_sizes_sum_to_micro_count():
    n, ga = 100, 16
    seen = {}
    for i in range(n): seen.setdefault(i // ga, U.window_size(i, n, ga))
    assert sum(seen.values()) == n and seen[6] == 4


def test_verify_sums_and_row_counts(tmp_path):
    p = tmp_path / "train.jsonl.gz"; gzip.open(p, "wt").write(json.dumps({"a": 1}) + "\n")
    (tmp_path / "SHA256SUMS").write_text(f"{U.sha256_file(p)}  train.jsonl.gz\n")
    U.verify_sums(str(tmp_path / "SHA256SUMS"), [str(p)])
    gzip.open(p, "wt").write(json.dumps({"a": 2}) + "\n")
    with pytest.raises(SystemExit): U.verify_sums(str(tmp_path / "SHA256SUMS"), [str(p)])
    with pytest.raises(SystemExit): U.verify_sums(str(tmp_path / "missing"), [str(p)])
    assert len(U.read_rows(str(p))) == 1
    with pytest.raises(SystemExit): U.check_row_counts({"train": 1}, {"train": 2})


def test_truncate_log_removes_duplicate_steps(tmp_path):
    p = tmp_path / "l.jsonl"; p.write_text("".join(json.dumps(r) + "\n" for r in [{"step": 1}, {"step": 2}, {"midcheck": {}, "step": 2}, {"step": 3}]))
    assert U.truncate_log(str(p), 2) == 1
    assert [json.loads(l).get("step") for l in open(p)] == [1, 2, 2]


def test_drop_check():
    U.drop_check(1, 100, 0.02)
    with pytest.raises(SystemExit): U.drop_check(5, 100, 0.02)
