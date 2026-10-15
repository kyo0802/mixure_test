# V1D resource measurements

| Attempt | Input tokens | Visual tokens | Generated | EOS | Cap | Gen seconds | E2E seconds | Allocated GiB | Reserved GiB | CPU RSS GiB |
|---|---|---|---|---|---|---|---|---|---|---|
| R01_C01 | 3973 | 2016 | 183 | True | False | 61.146 | 62.218 | 6.317 | 6.865 | 2.539 |
| R02_C06 | 2162 | 240 | 572 | True | False | 155.538 | 155.588 | 6.01 | 6.865 | 3.232 |
| R03_C08 | 2930 | 1008 | 356 | True | False | 98.637 | 98.748 | 6.15 | 6.865 | 3.66 |
| R04_C03 | 3973 | 2016 | 347 | True | False | 50.385 | 50.537 | 6.317 | 6.865 | 3.845 |
| R05_C04 | 2162 | 240 | 569 | True | False | 12.366 | 12.41 | 6.01 | 6.865 | 3.856 |
| R06_C07 | 2930 | 1008 | 237 | True | False | 5.655 | 5.756 | 6.15 | 6.865 | 3.877 |
| R07_C02 | 3973 | 2016 | 347 | True | False | 8.519 | 8.66 | 6.317 | 6.865 | 3.836 |
| R08_C05 | 2162 | 240 | 569 | True | False | 12.413 | 12.457 | 6.01 | 6.865 | 3.857 |

Model load=23.780862699999943s; total generation=404.66026130000023s; supervisor wall=450.6099999999999s; global GPU observed peak=8444.0MiB; owned-tree CPU RSS observed peak=4.4870147705078125GiB.

No warmup; first-condition cold/startup effects retained, no steady-state benchmark claim. PyTorch allocated/reserved peaks differ from sampled global GPU memory. Supervisor covers complete owned process tree, nominal1s with variable NVIDIA-SMI overhead, not absolute continuous peaks. Effective kwargs are in each runtime receipt (greedy/1024/seed42/300s); inactive checkpoint temperature warning retained, no temperature argument forced.
