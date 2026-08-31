# Assumptions

| ID | Assumption | Status |
|---|---|---|
| A1 | This repository was intentionally initialized from an empty workspace on 2026-09-01. | Confirmed by user |
| A2 | Ding-Jiang reproduction is pinned to arXiv:2407.21723v3 unless explicitly changed. | Active |
| A3 | Li et al. reproduction is pinned to arXiv:2604.07451v1 unless a newer version is explicitly selected. | Active |
| A4 | The 2x2 XOR quantum bias can be computed by reducing Tsirelson's vector optimization to a one-dimensional maximization over the inner product of Bob's two vectors. | Tested against CHSH and Ding Theorem 10 samples |
| A5 | Li Eq. 25 is implemented with right-bottom matrix entry `-P(1,1)` because Eq. 35 requires the CHSH limit `1/4 [[1,1],[1,-1]]`. | Active |
| A6 | Ding-Jiang's depolarizing `nu` and Li's combined infidelity `epsilon` are distinct model parameters. | Active |
| A7 | Figure reproduction tolerances remain unset until scripts generate numerical data rather than relying on plot images. | Active |
