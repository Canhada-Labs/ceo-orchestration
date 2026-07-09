---
name: pytorch-patterns
description: >
  Idiomatic PyTorch for robust, reproducible, memory-conscious training
  pipelines: device-agnostic placement, full seed control, explicit tensor
  shape tracking, clean nn.Module construction, weight initialisation,
  correct train/eval mode discipline, the standard training and validation
  loops, efficient Dataset/DataLoader configuration, variable-length
  collation, resumable checkpointing, and the performance levers (mixed
  precision, gradient checkpointing, torch.compile). Front-loads the
  autograd- and correctness-breaking anti-patterns: forgetting eval() at
  validation, in-place ops severing the graph, .item() before backward,
  moving the model to GPU inside the loop, and the pickle-RCE risk of loading
  checkpoints without weights_only. Use when writing or reviewing models,
  training scripts, or data pipelines, or when tuning GPU memory and speed.
version: 1.0.0
metadata:
  activation_triggers:
    - "torch|pytorch"
    - "nn\\.Module"
    - "DataLoader|Dataset"
    - "optimizer|zero_grad|backward"
    - "autocast|GradScaler|amp"
    - "torch\\.compile|checkpoint"
    - "cuda|state_dict|weights_only"
  paths:
    - "**/*.py"
  risk_class: low
  domain: data-ml
source: affaan-m/ecc@81af4076 skills/pytorch-patterns/
license: MIT
---

# PyTorch Patterns

Idiomatic PyTorch for training code that is portable across hardware,
reproducible run-to-run, and honest about GPU memory. The through-line: keep
the model device-agnostic, control every source of randomness, track tensor
shapes explicitly, and never let a convenience call quietly detach the
autograd graph.

## When to Activate

- Writing a new model, training script, or data pipeline.
- Reviewing deep-learning code for correctness or efficiency.
- Debugging a training loop, a data loader, or a loss that will not move.
- Tuning GPU memory footprint or training throughput.
- Setting up an experiment that must be reproducible.

## Version Note

The AMP and compilation surfaces have moved. This skill uses the current
`torch.amp` namespace (`torch.amp.autocast("cuda", ...)`,
`torch.amp.GradScaler("cuda")`) rather than the older `torch.cuda.amp`, and
`torch.compile` (available from 2.0). If you are on an older build, the
concepts hold but the import paths differ — check `torch.__version__`.

Type hints below use `typing.Optional[...]` / `typing.Tuple[...]` rather than
PEP 604 `X | None`, so the snippets stay valid on Python 3.9. Add
`from __future__ import annotations` at the top of a module if you prefer the
`|` spelling on 3.9.

## Core Principles

### 1. Device-agnostic placement

Resolve the device once, then move the model and every batch onto it. Never
hardcode `.cuda()` — it turns "no GPU available" into a crash instead of a
CPU fallback.

```python
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = MyModel().to(device)
# per batch:
data = data.to(device)

# Avoid: hard-fails on any CPU-only machine
model = MyModel().cuda()
```

### 2. Reproducibility first

Seed every RNG your pipeline touches — PyTorch (CPU and CUDA), NumPy, and
Python's `random`. For bit-reproducible runs also force deterministic cuDNN,
accepting the throughput cost.

```python
def set_seed(seed: int = 42) -> None:
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    random.seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False  # benchmark=True is faster but non-deterministic
```

`cudnn.benchmark = True` auto-tunes convolution algorithms and is faster for
fixed input sizes — but it makes runs non-deterministic. Pick one; do not
expect both.

### 3. Explicit shape management

Annotate the shape after each transform in `forward`. A one-line comment per
step turns a silent `view`/`reshape` mismatch into something you can read.

```python
def forward(self, x: torch.Tensor) -> torch.Tensor:
    # x: (N, C, H, W)
    x = self.conv1(x)            # (N, 32, H, W)
    x = self.pool(x)             # (N, 32, H//2, W//2)
    x = x.view(x.size(0), -1)    # (N, 32 * H//2 * W//2)
    return self.fc(x)            # (N, num_classes)
```

Prefer `reshape` over `view` when a tensor may be non-contiguous (e.g. after
a `permute` or `transpose`); `view` raises on non-contiguous memory.

## Model Architecture

### Build submodules in `__init__`, not `forward`

Every learnable layer must be constructed once in `__init__` so its
parameters register with the module. Constructing a layer (or its weights)
inside `forward` creates fresh, untrained parameters on every call and they
never appear in `model.parameters()`.

```python
class ImageClassifier(nn.Module):
    def __init__(self, num_classes: int, dropout: float = 0.5) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(64 * 16 * 16, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = x.view(x.size(0), -1)
        return self.classifier(x)
```

### Weight initialisation

Initialise explicitly rather than trusting layer defaults, especially for
deep nets. `model.apply(fn)` walks every submodule.

```python
def init_weights(module: nn.Module) -> None:
    if isinstance(module, nn.Linear):
        nn.init.kaiming_normal_(module.weight, mode="fan_out", nonlinearity="relu")
        if module.bias is not None:
            nn.init.zeros_(module.bias)
    elif isinstance(module, nn.Conv2d):
        nn.init.kaiming_normal_(module.weight, mode="fan_out", nonlinearity="relu")
    elif isinstance(module, nn.BatchNorm2d):
        nn.init.ones_(module.weight)
        nn.init.zeros_(module.bias)

model.apply(init_weights)
```

## Training Loops

### Train step

Set train mode, clear grads with `set_to_none=True` (frees the buffers and is
marginally faster), run the forward under autocast when using mixed
precision, clip gradients, and step. Accumulate the loss as a Python float
with `.item()` for logging only.

```python
from typing import Optional

def train_one_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
    scaler: Optional[torch.amp.GradScaler] = None,
) -> float:
    model.train()  # dropout on, BatchNorm updates running stats
    total_loss = 0.0

    for data, target in dataloader:
        data, target = data.to(device), target.to(device)
        optimizer.zero_grad(set_to_none=True)

        with torch.amp.autocast("cuda", enabled=scaler is not None):
            output = model(data)
            loss = criterion(output, target)

        if scaler is not None:
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)  # unscale before clipping
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            scaler.step(optimizer)
            scaler.update()
        else:
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

        total_loss += loss.item()

    return total_loss / len(dataloader)
```

Note the ordering under AMP: `scaler.scale(loss).backward()`, then
`scaler.unscale_(optimizer)` **before** `clip_grad_norm_`, then
`scaler.step` / `scaler.update`. Clipping scaled gradients clips the wrong
magnitude.

### Validation step

Set eval mode and disable gradients. `@torch.no_grad()` as a decorator is
cleaner than wrapping the body and covers early returns.

```python
from typing import Tuple

@torch.no_grad()
def evaluate(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> Tuple[float, float]:
    model.eval()  # dropout off, BatchNorm uses running stats
    total_loss, correct, total = 0.0, 0, 0

    for data, target in dataloader:
        data, target = data.to(device), target.to(device)
        output = model(data)
        total_loss += criterion(output, target).item()
        correct += (output.argmax(1) == target).sum().item()
        total += target.size(0)

    return total_loss / len(dataloader), correct / total
```

`model.eval()` and `torch.no_grad()` are independent and you need both:
`eval()` switches layer behaviour (dropout, BatchNorm), `no_grad()` stops
building the autograd graph. Forgetting `eval()` is the most common silent
validation bug — see Anti-Patterns.

## Data Pipeline

### Custom Dataset

A `Dataset` needs `__len__` and `__getitem__`. Keep per-item work light and
push heavy transforms into the loader's workers.

```python
from typing import Optional, Tuple

class ImageDataset(Dataset):
    def __init__(
        self,
        image_dir: str,
        labels: dict,
        transform: Optional[transforms.Compose] = None,
    ) -> None:
        self.image_paths = list(Path(image_dir).glob("*.jpg"))
        self.labels = labels
        self.transform = transform

    def __len__(self) -> int:
        return len(self.image_paths)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        img = Image.open(self.image_paths[idx]).convert("RGB")
        label = self.labels[self.image_paths[idx].stem]
        if self.transform:
            img = self.transform(img)
        return img, label
```

### DataLoader configuration

The defaults (`num_workers=0`, no pinned memory) leave the GPU starved. Load
in parallel workers, pin host memory for a faster host→device copy, and keep
workers alive across epochs.

```python
dataloader = DataLoader(
    dataset,
    batch_size=32,
    shuffle=True,             # training only; never shuffle eval
    num_workers=4,            # parallel loading
    pin_memory=True,          # faster host -> GPU copy
    persistent_workers=True,  # don't respawn workers each epoch
    drop_last=True,           # stable batch size (matters for BatchNorm)
)
```

### Variable-length collation

For sequences, pad to the batch's max length in a `collate_fn`.

```python
from typing import List, Tuple

def collate_fn(
    batch: List[Tuple[torch.Tensor, int]],
) -> Tuple[torch.Tensor, torch.Tensor]:
    sequences, labels = zip(*batch)
    padded = nn.utils.rnn.pad_sequence(sequences, batch_first=True, padding_value=0)
    return padded, torch.tensor(labels)

dataloader = DataLoader(dataset, batch_size=32, collate_fn=collate_fn)
```

## Checkpointing

Save the full training state — model, optimizer, epoch, metrics — so a run
can resume, not just weights. On load, pass `weights_only=True` (see the
security note) and map to CPU first so a checkpoint saved on GPU loads on any
machine.

```python
def save_checkpoint(model, optimizer, epoch: int, loss: float, path: str) -> None:
    torch.save(
        {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "loss": loss,
        },
        path,
    )

def load_checkpoint(path: str, model, optimizer=None) -> dict:
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    model.load_state_dict(checkpoint["model_state_dict"])
    if optimizer is not None:
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    return checkpoint
```

> Security: `torch.load` historically unpickled arbitrary objects, so a
> malicious checkpoint could execute code on load. Always pass
> `weights_only=True` for anything you did not produce yourself, and treat
> third-party checkpoints as untrusted input. Save with `state_dict()`, not
> the whole model object — pickling a full `nn.Module` binds the file to your
> exact class layout and is far more fragile.

## Performance Levers

### Mixed precision (AMP)

Run the forward and loss in lower precision under `autocast`, and use a
`GradScaler` so small gradients do not underflow to zero. Often ~2x
throughput and roughly half the activation memory on supported GPUs.

```python
scaler = torch.amp.GradScaler("cuda")
for data, target in dataloader:
    with torch.amp.autocast("cuda"):
        output = model(data)
        loss = criterion(output, target)
    scaler.scale(loss).backward()
    scaler.step(optimizer)
    scaler.update()
    optimizer.zero_grad(set_to_none=True)
```

### Gradient checkpointing (trade compute for memory)

Recompute intermediate activations during the backward pass instead of
holding them — lets a larger model fit at the cost of extra forward compute.

```python
from torch.utils.checkpoint import checkpoint

class LargeModel(nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = checkpoint(self.block1, x, use_reentrant=False)
        x = checkpoint(self.block2, x, use_reentrant=False)
        return self.head(x)
```

Pass `use_reentrant=False` — the reentrant path is legacy and interacts badly
with some inputs.

### torch.compile (2.0+)

JIT-compile the model into fused kernels. Wrap once after moving to device.

```python
model = torch.compile(MyModel().to(device), mode="reduce-overhead")
# modes: "default" (safe) · "reduce-overhead" · "max-autotune" (slowest to compile)
```

The first step or two pays a compilation cost; steady-state is faster.

## Quick Reference

| Idiom | Purpose |
|---|---|
| `model.train()` / `model.eval()` | Switch layer behaviour before the loop |
| `torch.no_grad()` / `@torch.no_grad()` | Stop building the graph for inference |
| `optimizer.zero_grad(set_to_none=True)` | Cheaper, more thorough grad clearing |
| `.to(device)` | Device-agnostic placement |
| `torch.amp.autocast` + `GradScaler` | Mixed precision without gradient underflow |
| `pin_memory=True` | Faster host→GPU transfer |
| `torch.compile` | Kernel fusion for speed (2.0+) |
| `weights_only=True` | Safe checkpoint loading |
| `torch.manual_seed` (+ NumPy, random) | Reproducible runs |
| `torch.utils.checkpoint` | Fit larger models by recomputing activations |

## Anti-Patterns

```python
# 1) Forgetting eval() — dropout still fires, BatchNorm uses batch stats
model.train()
with torch.no_grad():
    output = model(val_data)          # WRONG: metrics are noisy and wrong
# Right:
model.eval()
with torch.no_grad():
    output = model(val_data)

# 2) In-place ops that sever autograd
x = F.relu(x, inplace=True)           # can corrupt the graph
x += residual                          # in-place add on a graph tensor
# Right:
x = F.relu(x)
x = x + residual

# 3) Moving the model to GPU inside the loop
for data, target in dataloader:
    model = model.cuda()               # re-copies the model every iteration
# Right: move once, before the loop
model = model.to(device)
for data, target in dataloader:
    data, target = data.to(device), target.to(device)

# 4) .item() before backward — detaches from the graph
loss = criterion(output, target).item()
loss.backward()                        # error: a float has no backward()
# Right: keep the tensor; call .item() only to log
loss = criterion(output, target)
loss.backward()
print(f"loss={loss.item():.4f}")

# 5) Saving the whole model object
torch.save(model, "model.pt")          # fragile, tied to class layout
# Right: save the state_dict
torch.save(model.state_dict(), "model.pt")
```

When memory or speed is the question, measure before guessing: profile with
`torch.profiler` and read the allocator with `torch.cuda.memory_summary()`.

## Changelog

- 1.0.0 — Initial clean-room authoring. Covers device-agnostic placement,
  full seed control, explicit shape tracking, module construction and weight
  init, train/eval discipline, the standard train and validation loops,
  Dataset/DataLoader configuration and variable-length collation, resumable
  checkpointing with the `weights_only` security note, the performance levers
  (AMP, gradient checkpointing, `torch.compile`), and the five autograd- and
  correctness-breaking anti-patterns. Type hints written for Python 3.9
  compatibility (`typing.Optional`/`Tuple`, current `torch.amp` namespace).
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=9bd2169e09e8cfc7677ffbbfd5e7186d1782fa8be257d42eb69a17d2d44f4778
