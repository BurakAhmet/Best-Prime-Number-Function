# C / Rust / Go bindings

The interesting engine is the OpenMP core in `is_prime_data/wheel_core.c`,
not the Python wrapper. It exports two functions (see
[`include/best_prime.h`](https://github.com/BurakAhmet/Best-Prime-Number-Function/blob/main/include/best_prime.h)):

```c
int is_prime_u64_core(uint64_t n, int parallel);
int is_prime_u128_core(uint64_t lo, uint64_t hi, int parallel);
```

`parallel != 0` enables OpenMP; the boolean never depends on the thread
schedule. No stochastic Miller–Rabin.

## Build the shared library

```bash
# Linux / macOS (Homebrew libomp on Darwin)
make -C native
make -C native prefix=/usr/local install   # header + libbestprime + pkg-config
pkg-config --cflags --libs best_prime
```

Or `bash scripts/compile_wheel_core.sh` and load `is_prime_data/wheel_core.so`
with `dlopen` / `ctypes` (that is what Python does).

## C

```c
#include <best_prime.h>
#include <stdio.h>

int main(void) {
    printf("%d\n", best_prime_u64(17, 1));          /* 1 */
    printf("%d\n", best_prime_u64(100, 0));         /* 0 */
    return 0;
}
```

```bash
cc demo.c $(pkg-config --cflags --libs best_prime) -o demo
```

## Rust (`cc` / `libloading`)

```toml
# Cargo.toml
[build-dependencies]
cc = "1"
```

```rust
// build.rs — compile the generated C next to the crate
fn main() {
    cc::Build::new()
        .file("vendor/wheel_core.c")
        .flag_if_supported("-fopenmp")
        .flag_if_supported("-O3")
        .compile("bestprime");
    println!("cargo:rustc-link-lib=gomp");
}
```

```rust
extern "C" {
    fn is_prime_u64_core(n: u64, parallel: i32) -> i32;
}

pub fn is_prime_u64(n: u64) -> bool {
    unsafe { is_prime_u64_core(n, 1) != 0 }
}
```

Regenerate `wheel_core.c` with `python scripts/generate_wheel_core_c.py`
and vendor that file; do not commit a prebuilt `.so`.

## Go (`cgo`)

```go
package prime

/*
#cgo CFLAGS: -O3
#cgo LDFLAGS: -lbestprime -lm -fopenmp
#include <best_prime.h>
*/
import "C"

func IsPrimeU64(n uint64) bool {
    return C.is_prime_u64_core(C.uint64_t(n), 1) != 0
}
```

Install the library first (`make -C native install`) so `best_prime.h` and
`-lbestprime` resolve.

## What this does *not* cover

Python’s AKS / big-int path, `prime_count`, and factoring stay in
`best_prime`. The C core is the 64-bit and practical 128-bit trial engines
only.
