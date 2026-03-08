# thorvg-cython

Cython bindings for the [ThorVG](https://www.thorvg.org) vector graphics library.

## Overview

This package provides **direct C-level bindings** to ThorVG via Cython — no ctypes overhead.
It mirrors the `thorvg-python` API surface while delivering native-extension performance.

## Platform Support

| Platform | Linking Strategy |
|---|---|
| **iOS** (`sys.platform == "ios"`) | Links against `thorvg.xcframework` static slice |
| **macOS** (`sys.platform == "darwin"`) | Links against `libthorvg.a` or `libthorvg-1.dylib` |
| **Linux** | Links against `libthorvg.so` |
| **Windows** | Links against `thorvg.lib` / `thorvg-1.dll` |
| **Android** | Links against `libthorvg.so` |

## Building

### Prerequisites

- Python ≥ 3.9
- Cython ≥ 3.0
- ThorVG built with C API bindings (`-Dbindings=capi`)

### Quick Build (macOS)

```bash
# 1. Build ThorVG
cd /path/to/thorvg
export SDKROOT=$(xcrun --show-sdk-path)
meson setup builddir --buildtype=release --default-library=static -Dbindings=capi -Dloaders=svg,lottie,ttf
ninja -C builddir

# 2. Build the wheel
cd thorvg-cython
THORVG_ROOT=.. THORVG_LIB_DIR=../builddir/src pip install -e .
```

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `THORVG_ROOT` | Path to thorvg source root | Parent of this package |
| `THORVG_INCLUDE` | Path to `thorvg.h` | `$THORVG_ROOT/inc` |
| `THORVG_LIB_DIR` | Path to built libraries | `$THORVG_ROOT/output` |
| `THORVG_XCFRAMEWORK` | Path to `.xcframework` | `$THORVG_ROOT/output/thorvg.xcframework` |
| `THORVG_CAPI_INCLUDE` | Path to `thorvg_capi.h` | `$THORVG_ROOT/src/bindings/capi` |

### cibuildwheel

```bash
pip install cibuildwheel
cibuildwheel --platform macos
```

## Usage

```python
import thorvg_cython as tvg

with tvg.Engine(threads=2) as engine:
    canvas = tvg.SwCanvas()
    shape = tvg.Shape()
    shape.append_rect(0, 0, 100, 100, rx=10, ry=10)
    shape.set_fill_color(255, 0, 0)
    canvas.add(shape)
```

## License

MIT — same as ThorVG.
