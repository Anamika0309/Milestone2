# Microsoft Visual C++ Redistributable Installation

## Required for Phase 2 Dependencies

The Phase 2 retrieval components require Microsoft Visual C++ Redistributable to run PyTorch and sentence-transformers properly.

## Download Link

**Microsoft Visual C++ Redistributable 2022 (x64):**
https://aka.ms/vs/17/release/vc_redist.x64.exe

## Installation Steps

1. **Download:** Click the link above to download the installer
2. **Run:** Execute the downloaded installer
3. **Restart:** Restart your computer after installation
4. **Verify:** Re-run Phase 2 tests to confirm functionality

## Why This Is Needed

- **PyTorch:** Requires C++ runtime libraries
- **Sentence-Transformers:** Depends on PyTorch
- **BGE Models:** Require tensor operations
- **Cross-Encoder:** Uses transformer models

## Alternative: Use Mock Implementations

If you prefer not to install system dependencies, the existing Phase 2 components already include mock implementations that work without heavy dependencies:

- ✅ **Query Normalizer:** Works without external deps
- ✅ **Scheme Resolver:** Fully functional
- ✅ **Hybrid Retriever:** Mock fusion works
- ✅ **Confidence Gate:** Logic without ML deps
- ⚠️ **Cross-Encoder:** Mock version available

## Recommendation

**Install Visual C++ Redistributable** for full Phase 2 functionality with real BGE models and PyTorch-based retrieval.

**Use Mock Implementations** for immediate testing without system changes.
