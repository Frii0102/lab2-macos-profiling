# Battery-side energy estimate

Coarse system-level estimate at the battery terminals; not wall power or exact process energy.

| Version | Run | Sample window s | Battery energy J | Background W | Incremental estimate J |
|---|---:|---:|---:|---:|---:|
| O3 | 1 | 12.012 | 80.729 | 6.331 | 4.682 |

Amperage can be averaged/stale; polling faster does not increase sensor resolution.
Sampling window approximates process lifetime, with up to about one poll interval at boundaries.
Other apps, display, temperature, sensor lag and measurement overhead affect the result.
Negative incremental energy is retained, not hidden; repeat and inspect background drift.
No claim of exact attribution to the program. Do not mix with 2000-repeat time measurements.
Source: https://github.com/apple-oss-distributions/xnu/blob/main/iokit/IOKit/pwr_mgt/IOPMPowerSource.h
