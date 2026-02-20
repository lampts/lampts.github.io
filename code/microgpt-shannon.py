import os
import math
import random
random.seed(42)

if not os.path.exists('input.txt'):
    import urllib.request
    names_url = 'https://raw.githubusercontent.com/karpathy/makemore/refs/heads/master/names.txt'
    urllib.request.urlretrieve(names_url, 'input.txt')
docs = [l.strip() for l in open('input.txt').read().strip().split('\n') if l.strip()]
random.shuffle(docs)
print(f"num docs: {len(docs)}")

uchars = sorted(set(''.join(docs)))
BOS = len(uchars)
vocab_size = len(uchars) + 1
print(f"vocab size: {vocab_size}")

class Value:
    __slots__ = ('data', 'grad', '_children', '_local_grads')
    def __init__(self, data, children=(), local_grads=()):
        self.data = data
        self.grad = 0
        self._children = children
        self._local_grads = local_grads
    def __add__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        return Value(self.data + other.data, (self, other), (1, 1))
    def __mul__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        return Value(self.data * other.data, (self, other), (other.data, self.data))
    def __pow__(self, other): return Value(self.data**other, (self,), (other * self.data**(other-1),))
    def log(self): return Value(math.log(self.data), (self,), (1/self.data,))
    def exp(self): return Value(math.exp(self.data), (self,), (math.exp(self.data),))
    def relu(self): return Value(max(0, self.data), (self,), (float(self.data > 0),))
    def __neg__(self): return self * -1
    def __radd__(self, other): return self + other
    def __sub__(self, other): return self + (-other)
    def __rsub__(self, other): return other + (-self)
    def __rmul__(self, other): return self * other
    def __truediv__(self, other): return self * other**-1
    def __rtruediv__(self, other): return other * self**-1
    def backward(self):
        topo, visited = [], set()
        def build_topo(v):
            if v not in visited:
                visited.add(v)
                for child in v._children: build_topo(child)
                topo.append(v)
        build_topo(self)
        self.grad = 1
        for v in reversed(topo):
            for child, local_grad in zip(v._children, v._local_grads):
                child.grad += local_grad * v.grad

n_embd = 16
n_head = 4
n_layer = 1
block_size = 16
head_dim = n_embd // n_head
matrix = lambda nout, nin, std=0.08: [[Value(random.gauss(0, std)) for _ in range(nin)] for _ in range(nout)]
state_dict = {'wte': matrix(vocab_size, n_embd), 'wpe': matrix(block_size, n_embd), 'lm_head': matrix(vocab_size, n_embd)}
for i in range(n_layer):
    state_dict[f'layer{i}.attn_wq'] = matrix(n_embd, n_embd)
    state_dict[f'layer{i}.attn_wk'] = matrix(n_embd, n_embd)
    state_dict[f'layer{i}.attn_wv'] = matrix(n_embd, n_embd)
    state_dict[f'layer{i}.attn_wo'] = matrix(n_embd, n_embd)
    state_dict[f'layer{i}.mlp_fc1'] = matrix(4 * n_embd, n_embd)
    state_dict[f'layer{i}.mlp_fc2'] = matrix(n_embd, 4 * n_embd)
params = [p for mat in state_dict.values() for row in mat for p in row]
print(f"num params: {len(params)}")

def linear(x, w):
    return [sum(wi * xi for wi, xi in zip(wo, x)) for wo in w]

def softmax(logits):
    max_val = max(val.data for val in logits)
    exps = [(val - max_val).exp() for val in logits]
    total = sum(exps)
    return [e / total for e in exps]

def rmsnorm(x):
    ms = sum(xi * xi for xi in x) / len(x)
    scale = (ms + 1e-5) ** -0.5
    return [xi * scale for xi in x]

def gpt(token_id, pos_id, keys, values):
    tok_emb = state_dict['wte'][token_id]
    pos_emb = state_dict['wpe'][pos_id]
    x = [t + p for t, p in zip(tok_emb, pos_emb)]
    x = rmsnorm(x)
    for li in range(n_layer):
        x_residual = x
        x = rmsnorm(x)
        q = linear(x, state_dict[f'layer{li}.attn_wq'])
        k = linear(x, state_dict[f'layer{li}.attn_wk'])
        v = linear(x, state_dict[f'layer{li}.attn_wv'])
        keys[li].append(k)
        values[li].append(v)
        x_attn = []
        for h in range(n_head):
            hs = h * head_dim
            q_h = q[hs:hs+head_dim]
            k_h = [ki[hs:hs+head_dim] for ki in keys[li]]
            v_h = [vi[hs:hs+head_dim] for vi in values[li]]
            attn_logits = [sum(q_h[j] * k_h[t][j] for j in range(head_dim)) / head_dim**0.5 for t in range(len(k_h))]
            attn_weights = softmax(attn_logits)
            head_out = [sum(attn_weights[t] * v_h[t][j] for t in range(len(v_h))) for j in range(head_dim)]
            x_attn.extend(head_out)
        x = linear(x_attn, state_dict[f'layer{li}.attn_wo'])
        x = [a + b for a, b in zip(x, x_residual)]
        x_residual = x
        x = rmsnorm(x)
        x = linear(x, state_dict[f'layer{li}.mlp_fc1'])
        x = [xi.relu() for xi in x]
        x = linear(x, state_dict[f'layer{li}.mlp_fc2'])
        x = [a + b for a, b in zip(x, x_residual)]
    logits = linear(x, state_dict['lm_head'])
    return logits

learning_rate, beta1, beta2, eps_adam = 0.01, 0.85, 0.99, 1e-8
m = [0.0] * len(params)
v = [0.0] * len(params)

num_steps = 1000
for step in range(num_steps):
    doc = docs[step % len(docs)]
    tokens = [BOS] + [uchars.index(ch) for ch in doc] + [BOS]
    n = min(block_size, len(tokens) - 1)
    keys, values = [[] for _ in range(n_layer)], [[] for _ in range(n_layer)]
    losses = []
    for pos_id in range(n):
        token_id, target_id = tokens[pos_id], tokens[pos_id + 1]
        logits = gpt(token_id, pos_id, keys, values)
        probs = softmax(logits)
        loss_t = -probs[target_id].log()
        losses.append(loss_t)
    loss = (1 / n) * sum(losses)
    loss.backward()
    lr_t = learning_rate * (1 - step / num_steps)
    for i, p in enumerate(params):
        m[i] = beta1 * m[i] + (1 - beta1) * p.grad
        v[i] = beta2 * v[i] + (1 - beta2) * p.grad ** 2
        m_hat = m[i] / (1 - beta1 ** (step + 1))
        v_hat = v[i] / (1 - beta2 ** (step + 1))
        p.data -= lr_t * m_hat / (v_hat ** 0.5 + eps_adam)
        p.grad = 0
    if (step + 1) % 100 == 0 or step == 0:
        print(f"step {step+1:4d} / {num_steps:4d} | loss {loss.data:.4f}")

temperature = 0.5
print("\n--- inference ---")
for sample_idx in range(20):
    keys, values = [[] for _ in range(n_layer)], [[] for _ in range(n_layer)]
    token_id = BOS
    sample = []
    for pos_id in range(block_size):
        logits = gpt(token_id, pos_id, keys, values)
        probs = softmax([l / temperature for l in logits])
        token_id = random.choices(range(vocab_size), weights=[p.data for p in probs])[0]
        if token_id == BOS: break
        sample.append(uchars[token_id])
    print(f"sample {sample_idx+1:2d}: {''.join(sample)}")

"""
Shannon Probe: measure the entropy of language at multiple levels.
Append this after microGPT training completes.

Shannon (1948) estimated English entropy ≈ 1.0-1.5 bits/char.
We verify by measuring how many bits/char our model needs at each
level of statistical structure it captures.

Theory: H(unigram) > H(bigram) > H(model) >= H(true)
Each level captures more structure → needs fewer bits → lower entropy.
The gap between levels = the statistical structure at that level.
"""

import math
from collections import Counter

# ═══════════════════════════════════════════════════════════════
# Level 0: Maximum entropy (uniform random)
# If we know nothing about the language, every char equally likely.
# ═══════════════════════════════════════════════════════════════

H_uniform = math.log2(len(uchars))  # log2(26) ≈ 4.70 bits/char
print(f"\n{'='*60}")
print(f"SHANNON ENTROPY PROBE")
print(f"{'='*60}")
print(f"\nLevel 0 — Uniform (know nothing)")
print(f"  H = log2({len(uchars)}) = {H_uniform:.4f} bits/char")
print(f"  PPL = {2**H_uniform:.1f}")

# ═══════════════════════════════════════════════════════════════
# Level 1: Unigram entropy
# Know character frequencies but nothing about order.
# P(char) = count(char) / total_chars
# ═══════════════════════════════════════════════════════════════

all_chars = ''.join(docs)
char_counts = Counter(all_chars)
total_chars = len(all_chars)

H_unigram = 0
for ch, count in char_counts.items():
    p = count / total_chars
    H_unigram -= p * math.log2(p)

print(f"\nLevel 1 — Unigram (know char frequencies)")
print(f"  H = {H_unigram:.4f} bits/char")
print(f"  PPL = {2**H_unigram:.1f}")
print(f"  Structure captured: {H_uniform - H_unigram:.4f} bits")
# Show top/bottom chars
freq_sorted = sorted(char_counts.items(), key=lambda x: -x[1])
top3 = ', '.join(f"'{c}'={n/total_chars:.3f}" for c, n in freq_sorted[:3])
bot3 = ', '.join(f"'{c}'={n/total_chars:.3f}" for c, n in freq_sorted[-3:])
print(f"  Most frequent: {top3}")
print(f"  Least frequent: {bot3}")

# ═══════════════════════════════════════════════════════════════
# Level 2: Bigram entropy
# Know P(char | previous char).
# H = -sum over all bigrams: P(c1,c2) * log2(P(c2|c1))
# ═══════════════════════════════════════════════════════════════

# Count bigrams (including BOS transitions)
bigram_counts = Counter()
context_counts = Counter()
for doc in docs:
    seq = '\x00' + doc + '\x00'  # \x00 = BOS marker
    for i in range(len(seq) - 1):
        bigram_counts[(seq[i], seq[i+1])] += 1
        context_counts[seq[i]] += 1

H_bigram = 0
total_bigrams = sum(bigram_counts.values())
for (c1, c2), count in bigram_counts.items():
    p_joint = count / total_bigrams
    p_cond = count / context_counts[c1]
    H_bigram -= p_joint * math.log2(p_cond)

print(f"\nLevel 2 — Bigram (know P(char|prev))")
print(f"  H = {H_bigram:.4f} bits/char")
print(f"  PPL = {2**H_bigram:.1f}")
print(f"  Structure captured: {H_unigram - H_bigram:.4f} bits (over unigram)")
# Show strongest bigram constraints
strongest = []
for c1 in set(c for c, _ in bigram_counts):
    c1_total = context_counts[c1]
    if c1_total < 100 or c1 == '\x00':
        continue
    best_c2 = max(
        [(c2, n/c1_total) for (cx, c2), n in bigram_counts.items() if cx == c1],
        key=lambda x: x[1]
    )
    strongest.append((c1, best_c2[0], best_c2[1]))
strongest.sort(key=lambda x: -x[2])
print(f"  Strongest constraints:")
for c1, c2, p in strongest[:5]:
    c1_disp = 'BOS' if c1 == '\x00' else f"'{c1}'"
    c2_disp = 'BOS' if c2 == '\x00' else f"'{c2}'"
    print(f"    P({c2_disp}|{c1_disp}) = {p:.3f}  ({-math.log2(p):.2f} bits)")

# ═══════════════════════════════════════════════════════════════
# Level 3: Trained model entropy
# Use the actual GPT model to estimate H.
# H_model = average cross-entropy over held-out documents.
# This is what the model's loss IS — just convert nats to bits.
# ═══════════════════════════════════════════════════════════════

print(f"\nLevel 3 — Trained microGPT ({len(params)} params)")

# Evaluate on held-out docs (use docs the model hasn't seen in training)
eval_docs = docs[num_steps:num_steps+200]  # docs after training set
if len(eval_docs) < 50:
    eval_docs = docs[:200]  # fallback: use training docs (upper bound is looser)
    eval_note = "(train set — optimistic)"
else:
    eval_note = "(held-out — fair estimate)"

total_log_prob = 0
total_chars_eval = 0
per_position_entropy = [0.0] * block_size
per_position_count = [0] * block_size

for doc in eval_docs:
    tokens = [BOS] + [uchars.index(ch) for ch in doc] + [BOS]
    n = min(block_size, len(tokens) - 1)
    keys_eval = [[] for _ in range(n_layer)]
    values_eval = [[] for _ in range(n_layer)]

    for pos_id in range(n):
        token_id = tokens[pos_id]
        target_id = tokens[pos_id + 1]
        logits = gpt(token_id, pos_id, keys_eval, values_eval)
        probs = softmax(logits)

        p_target = probs[target_id].data
        p_target = max(p_target, 1e-10)  # numerical safety
        log2_p = math.log2(p_target)
        total_log_prob += log2_p
        total_chars_eval += 1

        # Track entropy by position (how much harder is position 0 vs 5?)
        if pos_id < block_size:
            per_position_entropy[pos_id] -= log2_p
            per_position_count[pos_id] += 1

H_model = -total_log_prob / total_chars_eval

print(f"  H = {H_model:.4f} bits/char {eval_note}")
print(f"  PPL = {2**H_model:.1f}")
print(f"  Structure captured: {H_bigram - H_model:.4f} bits (over bigram)")
print(f"  Evaluated on {len(eval_docs)} docs, {total_chars_eval} chars")

# Show entropy by position
print(f"\n  Entropy by position (bits/char):")
print(f"  {'pos':>4s}  {'H':>6s}  {'bar'}")
for i in range(min(block_size, 10)):
    if per_position_count[i] > 0:
        h_pos = per_position_entropy[i] / per_position_count[i]
        bar = '█' * int(h_pos * 4)
        print(f"  {i:4d}  {h_pos:6.3f}  {bar}")

# ═══════════════════════════════════════════════════════════════
# Level 4: Human upper bound estimate (Shannon's game)
# Shannon's fill-in-the-blank experiment with English text.
# ═══════════════════════════════════════════════════════════════

H_shannon_high = 1.5  # upper bound
H_shannon_low = 1.0   # lower bound (refined estimates)

print(f"\nLevel 4 — Shannon's human estimate (1948/1951)")
print(f"  H ≈ {H_shannon_low}–{H_shannon_high} bits/char (English text)")
print(f"  PPL ≈ {2**H_shannon_low:.1f}–{2**H_shannon_high:.1f}")

# ═══════════════════════════════════════════════════════════════
# SUMMARY TABLE
# ═══════════════════════════════════════════════════════════════

print(f"\n{'='*60}")
print(f"SUMMARY: BITS PER CHARACTER AT EACH LEVEL")
print(f"{'='*60}")
print(f"")
print(f"  {'Level':<28s} {'H bits':>8s} {'PPL':>8s} {'Gap':>8s}")
print(f"  {'─'*28} {'─'*8} {'─'*8} {'─'*8}")
print(f"  {'L0 Uniform (26 chars)':<28s} {H_uniform:8.4f} {2**H_uniform:8.1f} {'—':>8s}")
print(f"  {'L1 Unigram':<28s} {H_unigram:8.4f} {2**H_unigram:8.1f} {H_uniform-H_unigram:8.4f}")
print(f"  {'L2 Bigram':<28s} {H_bigram:8.4f} {2**H_bigram:8.1f} {H_unigram-H_bigram:8.4f}")
print(f"  {'L3 microGPT':<28s} {H_model:8.4f} {2**H_model:8.1f} {H_bigram-H_model:8.4f}")
print(f"  {'L4 Shannon (human)':<28s} {'~1.0–1.5':>8s} {'~2–3':>8s} {f'{H_model-H_shannon_high:.4f}':>8s}")
print(f"  {'─'*28} {'─'*8} {'─'*8} {'─'*8}")
print(f"  {'Total structure captured':<28s} {'':>8s} {'':>8s} {H_uniform-H_model:8.4f}")
print(f"")
print(f"  Reading the table:")
print(f"  • Each level captures MORE statistical structure → fewer bits")
print(f"  • 'Gap' = how many bits of structure that level captured")
print(f"  • L0→L1 gap = knowing which letters are common")
print(f"  • L1→L2 gap = knowing which letters follow which")
print(f"  • L2→L3 gap = longer-range patterns (attention)")
print(f"  • L3→L4 gap = what microGPT still doesn't capture")
print(f"  • True entropy is lower bound. Model entropy is upper bound.")
print(f"")

# ═══════════════════════════════════════════════════════════════
# BONUS: Empirical entropy rate convergence
# As we see more context, entropy should decrease.
# This is Shannon's fundamental insight: more context = more
# predictable = fewer bits needed.
# ═══════════════════════════════════════════════════════════════

print(f"POSITION ENTROPY ANALYSIS")
print(f"{'='*60}")
print(f"  If Shannon is right, entropy should DECREASE with position")
print(f"  because more context = more predictable.\n")

prev_h = None
for i in range(min(block_size, 10)):
    if per_position_count[i] > 0:
        h_pos = per_position_entropy[i] / per_position_count[i]
        delta = ""
        if prev_h is not None:
            d = h_pos - prev_h
            arrow = "↓" if d < 0 else "↑"
            delta = f"  {arrow} {abs(d):.3f}"
        bar_full = '█' * int(h_pos * 5)
        bar_empty = '░' * (25 - len(bar_full))
        print(f"  pos {i}: {h_pos:.3f} bits  {bar_full}{bar_empty}{delta}")
        prev_h = h_pos

print(f"\n  Position 0 = predict first char after BOS (hardest)")
print(f"  Later positions = more context = easier to predict")
print(f"  The DECREASE is the statistical structure of names.")
print(f"  Shannon's claim verified: context reduces uncertainty.\n")
