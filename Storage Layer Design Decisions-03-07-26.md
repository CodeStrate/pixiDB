# pixiDB — Storage Layer Design Decisions

## Architecture

Three-layer storage stack, outermost layer is the public API:

```
CSRIndexing  (public API — secondary index + delegates to buffer)
    └── CSRBuffer  (write path — pending edges, compaction trigger)
            ├── CSRHash  (node registry — string ID ↔ integer index)
            └── CSR  (raw arrays — indptr/indices/edge_props)
```

All three internal classes live in `csr_store.py` to avoid circular imports (CSRHash needed CSRBuffer for `neighbors`, CSRBuffer needed CSRHash for node lookup). Methods prefixed `_` are internal by convention.

---

## CSR Representation

**Why CSR over adjacency list:** Adjacency lists have O(degree) neighbor lookup and poor cache locality. CSR stores all edges as contiguous arrays — neighbor lookup is a single array slice `indices[indptr[src]:indptr[src+1]]`, O(1) index into contiguous memory.

**Three arrays:**
- `indptr` (IA): length `num_nodes + 1`, `indptr[i]` is the start position of node i's edges in `indices`
- `indices` (JA): destination node indices, flattened across all rows
- `edge_props` (A): edge properties (Python dicts), parallel to `indices`

**`csr_from_arrays` classmethod:** Alternate constructor for building CSR directly from pre-built arrays (no edge list, no sort/count step). `num_nodes` is recoverable as `len(indptr) - 1`.

**Known gap vs scipy:** Within each source row, destination indices are in insertion order, not sorted. scipy guarantees sorted column indices. Secondary sort by dest not implemented in v1.

---

## Pending Edge Buffer

**Why:** CSR is immutable once built — rebuilding on every insert is O(E). Instead, new edges go to a `defaultdict(list)` buffer keyed by `src_idx → [(dst_idx, props), ...]`. Compaction rebuilds CSR only when `pendingCount >= threshold`.

**Reads merge both sources:** `neighbors` checks CSR (if built) + buffer. A node's edges are always fully visible regardless of compaction state.

**Compaction:** Collects all edges from CSR arrays + buffer, sorts by source, rebuilds CSR via `_build_csr`, clears buffer. `num_nodes` comes from the hash (not edges) so nodes with no edges are not dropped.

**Threshold:** Caller-configurable. Large threshold = fewer compactions, more buffer reads. Small threshold = CSR stays fresh, more rebuild cost.

---

## Hash Index

**Why Python dicts:** O(1) average lookup and insert, auto-resize before collisions, no external deps. Worst case O(n) only under pathological hash collisions.

**Three dicts:**
- `node_to_idx`: `str → int` (encode)
- `idx_to_node`: `int → str` (decode)
- `node_props`: `int → dict` (node properties by index)

**Duplicate guard:** `add_node_hash` raises `ValueError` on duplicate `node_id`. Silent overwrite would corrupt both dicts.

---

## Duplicate Edge Handling

Duplicate `(src, dst)` in the buffer merges props: `{**old_props, **new_props}`. New keys are added, existing keys overwritten by the newer value. `pendingCount` does not increment on a merge. Check is O(n) scan of `pendingBuffer[src]` list.

---

## Secondary Property Index

`secondary_index: defaultdict(list)` — maps `relation_type → [(src_idx, dst_idx), ...]`.

Built incrementally on every `add_edge` call through `CSRIndexing`. Deduplication: if `(src, dst)` already exists for a given `relation_type`, the append is skipped. Dedup check is O(n) — acceptable for v1, revisit if relation lists grow large.

**Known gap:** Index is not rebuilt on compaction — it stays consistent because it's populated at insert time, not derived from CSR arrays. But if CSR is loaded from disk (future persistence), index must be rebuilt from scratch.

---

## Known Gaps so far

| Gap | Impact | Fix |
|-----|--------|-----|
| No sorted indices within CSR rows | Minor — neighbors returned in insertion order | Secondary sort by dst in `_build_csr` |
| `edge_props` stored as object numpy array | No vectorized ops on props | Typed arrays or separate prop store |
| Secondary index dedup is O(n) | Slow for high-degree nodes with common relation types | Replace list with set (loses ordering) |
| Index not rebuilt on persistence load | Will be stale after deserialize | Rebuild index on load |
| No incoming edge index (CSC equivalent) | No reverse traversal without full scan | Second CSR stored column-wise |
