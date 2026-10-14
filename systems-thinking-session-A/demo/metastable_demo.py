#!/usr/bin/env python3
"""Mô phỏng metastable failure: một spike ngắn, ba chính sách retry khác nhau.

Chỉ dùng thư viện chuẩn của Python. Chạy:
    python3 metastable_demo.py
Kết quả: bảng tóm tắt trên terminal, metastable_demo.csv, metastable_demo.svg.

Mô hình
-------
- Server xử lý tối đa `capacity` req/s theo hàng đợi FIFO.
- Client đợi tối đa `timeout` giây. Quá hạn thì client bỏ cuộc và (tùy chính sách) retry.
- Server không biết client đã bỏ: request quá hạn vẫn nằm trong hàng đợi và vẫn
  tốn công xử lý. Công đó là "việc vô ích", không tính vào goodput.
- Trigger: DB chậm, capacity tụt xuống `trigger_capacity` trong [trigger_start, trigger_end).
  Sau đó capacity trở lại bình thường: trigger đã hết.
"""
import argparse
import heapq
import math
import random
from collections import deque


class Policy:
    def __init__(self, name, label, max_retries, backoff, queue_limit):
        self.name = name
        self.label = label
        self.max_retries = max_retries  # None = retry vô hạn
        self.backoff = backoff  # True = exponential backoff + full jitter
        self.queue_limit = queue_limit  # None = không shed; số = shed khi hàng đợi vượt


def poisson(rng, mean):
    limit = math.exp(-mean)
    k, p = 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def simulate(policy, args, seed):
    rng = random.Random(seed)
    dt = args.dt
    queue = deque()
    timeouts = []  # heap (deadline, seq, req)
    retries = []  # heap (time, seq, attempt)
    seq = 0
    budget = 0.0
    secs = int(args.duration)
    goodput = [0] * secs
    offered = [0] * secs
    wasted = [0] * secs
    qlen = [0] * secs
    failed_for_good = 0

    def second(t):
        return min(int(t), secs - 1)

    def fail(t, attempt):
        """Client thất bại ở lần thử `attempt`. Quyết định có retry không."""
        nonlocal seq, failed_for_good
        if policy.max_retries is not None and attempt >= policy.max_retries:
            failed_for_good += 1
            return
        if policy.backoff:
            delay = min(args.backoff_cap, args.backoff_base * (2 ** attempt)) * rng.random()
        else:
            delay = 0.0
        seq += 1
        heapq.heappush(retries, (t + delay, seq, attempt + 1))

    def submit(t, attempt):
        nonlocal seq
        offered[second(t)] += 1
        if policy.queue_limit is not None and len(queue) >= policy.queue_limit:
            fail(t, attempt)  # bị shed: lỗi ngay, không tốn công server
            return
        req = {"t": t, "attempt": attempt, "done": False}
        queue.append(req)
        seq += 1
        heapq.heappush(timeouts, (t + args.timeout, seq, req))

    steps = int(args.duration / dt)
    for i in range(steps):
        t = i * dt
        # 1. request mới
        for _ in range(poisson(rng, args.load * dt)):
            submit(t, 0)
        # 2. retry đến hạn
        while retries and retries[0][0] <= t:
            _, _, attempt = heapq.heappop(retries)
            submit(t, attempt)
        # 3. server làm việc
        in_trigger = args.trigger_start <= t < args.trigger_end
        capacity = args.trigger_capacity if in_trigger else args.capacity
        budget = min(budget + capacity * dt, 1.0 + capacity * dt)
        while budget >= 1.0 and queue:
            req = queue.popleft()
            budget -= 1.0
            if t - req["t"] <= args.timeout:
                req["done"] = True
                goodput[second(t)] += 1
            else:
                wasted[second(t)] += 1  # client đã bỏ đi, công này vô ích
        # 4. client hết kiên nhẫn
        while timeouts and timeouts[0][0] <= t:
            _, _, req = heapq.heappop(timeouts)
            if not req["done"]:
                fail(t, req["attempt"])
        qlen[second(t)] = len(queue)

    return {
        "goodput": goodput, "offered": offered, "wasted": wasted,
        "queue": qlen, "gave_up": failed_for_good,
    }


def recovery_time(goodput, args, window=5):
    """Số giây sau trigger_end để goodput giữ >= 90% tải bình thường trong `window` giây."""
    start = int(args.trigger_end)
    need = 0.9 * args.load
    for s in range(start, len(goodput) - window + 1):
        if all(g >= need for g in goodput[s:s + window]):
            return s - start
    return None


def avg(xs):
    return sum(xs) / len(xs) if xs else 0.0


def summarize(results, args):
    s0, s1 = int(args.trigger_start), int(args.trigger_end)
    print(f"\nTải {args.load:g} req/s, capacity {args.capacity:g} req/s, timeout {args.timeout:g}s.")
    print(f"Trigger: capacity tụt còn {args.trigger_capacity:g} req/s từ giây {s0} đến {s1}.\n")
    head = f"{'Kịch bản':<44}{'trước':>8}{'trigger':>9}{'+10s':>8}{'cuối':>8}  Hồi phục"
    print(head)
    print("-" * len(head))
    for pol, r in results:
        g = r["goodput"]
        before = avg(g[max(0, s0 - 10):s0])
        during = avg(g[s0:s1])
        after10 = avg(g[s1 + 8:s1 + 12])
        tail = avg(g[-10:])
        rec = recovery_time(g, args)
        verdict = f"sau {rec}s" if rec is not None else "KHÔNG hồi phục"
        print(f"{pol.label:<44}{before:>8.0f}{during:>9.0f}{after10:>8.0f}{tail:>8.0f}  {verdict}")
    print("\nCác cột là goodput trung bình (req/s): 10s trước trigger, trong trigger, quanh +10s sau trigger, 10s cuối.")


def write_csv(path, results, args):
    with open(path, "w", encoding="utf-8") as f:
        f.write("scenario,second,goodput,offered,wasted,queue\n")
        for pol, r in results:
            for s in range(len(r["goodput"])):
                f.write(f"{pol.name},{s},{r['goodput'][s]},{r['offered'][s]},{r['wasted'][s]},{r['queue'][s]}\n")


def write_svg(path, results, args):
    W, PW, PH, LEFT, TOP, GAP = 1200, 1000, 190, 150, 70, 70
    H = TOP + len(results) * (PH + GAP) + 30
    ymax = max(250.0, args.load * 3)
    n = len(results[0][1]["goodput"])

    def x(s):
        return LEFT + PW * s / (n - 1)

    def y(v, top):
        return top + PH - PH * min(v, ymax) / ymax

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Arial, sans-serif">',
           f'<rect width="{W}" height="{H}" fill="#F4F1EA"/>',
           f'<text x="{LEFT}" y="36" font-size="26" font-weight="bold" fill="#1B2029">Cùng một spike, ba chính sách retry: goodput theo thời gian</text>']
    for k, (pol, r) in enumerate(results):
        top = TOP + k * (PH + GAP)
        out.append(f'<text x="{LEFT}" y="{top - 12}" font-size="20" font-weight="bold" fill="#1B2029">{k + 1}. {pol.label}</text>')
        out.append(f'<rect x="{LEFT}" y="{top}" width="{PW}" height="{PH}" fill="#FBFAF6" stroke="#DDD8CB"/>')
        # vùng trigger
        out.append(f'<rect x="{x(args.trigger_start):.1f}" y="{top}" width="{x(args.trigger_end) - x(args.trigger_start):.1f}" height="{PH}" fill="#E8743B" opacity="0.18"/>')
        # trục y
        for v in (0, 100, 200):
            if v <= ymax:
                out.append(f'<line x1="{LEFT}" x2="{LEFT + PW}" y1="{y(v, top):.1f}" y2="{y(v, top):.1f}" stroke="#DDD8CB"/>')
                out.append(f'<text x="{LEFT - 10}" y="{y(v, top) + 6:.1f}" font-size="16" text-anchor="end" fill="#5A6270">{v}</text>')
        out.append(f'<text x="{LEFT - 62}" y="{top + PH / 2:.1f}" font-size="16" fill="#5A6270" transform="rotate(-90 {LEFT - 62} {top + PH / 2:.1f})" text-anchor="middle">req/s</text>')
        # capacity
        out.append(f'<line x1="{LEFT}" x2="{LEFT + PW}" y1="{y(args.capacity, top):.1f}" y2="{y(args.capacity, top):.1f}" stroke="#5A6270" stroke-dasharray="6 5"/>')
        # offered load (bị cắt ở ymax)
        pts = " ".join(f"{x(s):.1f},{y(v, top):.1f}" for s, v in enumerate(r["offered"]))
        out.append(f'<polyline points="{pts}" fill="none" stroke="#B4501D" stroke-width="2.5" stroke-dasharray="3 3"/>')
        # goodput
        pts = " ".join(f"{x(s):.1f},{y(v, top):.1f}" for s, v in enumerate(r["goodput"]))
        out.append(f'<polyline points="{pts}" fill="none" stroke="#1F6F68" stroke-width="4" stroke-linejoin="round"/>')
    # trục x + chú thích
    bottom = TOP + len(results) * (PH + GAP) - GAP
    for s in range(0, n, 10):
        out.append(f'<text x="{x(s):.1f}" y="{bottom + 24}" font-size="16" text-anchor="middle" fill="#5A6270">{s}s</text>')
    ly = bottom + 52
    out.append(f'<line x1="{LEFT}" x2="{LEFT + 40}" y1="{ly}" y2="{ly}" stroke="#1F6F68" stroke-width="4"/><text x="{LEFT + 50}" y="{ly + 6}" font-size="17" fill="#1B2029">Goodput (việc hữu ích)</text>')
    out.append(f'<line x1="{LEFT + 260}" x2="{LEFT + 300}" y1="{ly}" y2="{ly}" stroke="#B4501D" stroke-width="2.5" stroke-dasharray="3 3"/><text x="{LEFT + 310}" y="{ly + 6}" font-size="17" fill="#1B2029">Tải gửi tới (gồm retry, cắt ở {ymax:g})</text>')
    out.append(f'<line x1="{LEFT + 640}" x2="{LEFT + 680}" y1="{ly}" y2="{ly}" stroke="#5A6270" stroke-dasharray="6 5"/><text x="{LEFT + 690}" y="{ly + 6}" font-size="17" fill="#1B2029">Capacity</text>')
    out.append(f'<rect x="{LEFT + 800}" y="{ly - 10}" width="30" height="20" fill="#E8743B" opacity="0.3"/><text x="{LEFT + 840}" y="{ly + 6}" font-size="17" fill="#1B2029">Trigger</text>')
    out.append("</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--load", type=float, default=80, help="tải bình thường, req/s (80)")
    p.add_argument("--capacity", type=float, default=100, help="capacity bình thường, req/s (100)")
    p.add_argument("--trigger-capacity", type=float, default=30, help="capacity trong lúc trigger (30)")
    p.add_argument("--trigger-start", type=float, default=20)
    p.add_argument("--trigger-end", type=float, default=25)
    p.add_argument("--timeout", type=float, default=1.0, help="client timeout, giây (1.0)")
    p.add_argument("--duration", type=float, default=90)
    p.add_argument("--dt", type=float, default=0.05)
    p.add_argument("--backoff-base", type=float, default=0.5)
    p.add_argument("--backoff-cap", type=float, default=8.0)
    p.add_argument("--max-retries", type=int, default=3, help="số retry tối đa ở kịch bản 3 (3)")
    p.add_argument("--shed-after", type=float, default=0.5,
                   help="kịch bản 3 shed khi hàng đợi vượt capacity * giá trị này (0.5 giây công việc)")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--out", default="metastable_demo", help="tiền tố file đầu ra")
    args = p.parse_args()

    policies = [
        Policy("no_retry", "Không retry", 0, False, None),
        Policy("retry_forever", "Retry vô hạn, không backoff", None, False, None),
        Policy("backoff_shed", "Backoff + jitter + giới hạn retry + load shedding",
               args.max_retries, True, int(args.capacity * args.shed_after)),
    ]
    results = [(pol, simulate(pol, args, args.seed)) for pol in policies]
    summarize(results, args)
    write_csv(args.out + ".csv", results, args)
    write_svg(args.out + ".svg", results, args)
    print(f"\nĐã ghi {args.out}.csv và {args.out}.svg")


if __name__ == "__main__":
    main()
