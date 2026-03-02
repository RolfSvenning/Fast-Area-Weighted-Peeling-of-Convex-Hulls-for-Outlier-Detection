# Algorithm Pseudocode

This document records publication-level pseudocode for the planned algorithm
versions `V1` through `V4`.

The intent is architectural clarity rather than implementation syntax. Each
version states the maintained structures, the main loop, and the expected style
of updates at the same level of detail as the paper.

## `V1` Brute-Force Oracle

`V1` is the correctness oracle. It recomputes the convex hull after every
candidate deletion and chooses the unique hull vertex with maximum area
decrease.

```text
Algorithm V1_BruteForceWeightedPeeling(P)
Input:
    A set P of n points in the plane

active_points <- P
peel_order <- empty list
area_decreases <- empty list
hulls <- empty list

while |active_points| > 3
    H <- CH(active_points)
    best_vertex <- null
    best_decrease <- -infinity
    second_best_decrease <- -infinity

    for each vertex u in H
        P_u <- active_points \ {u}
        H_u <- CH(P_u)
        delta <- area(H) - area(H_u)

        if delta > best_decrease
            second_best_decrease <- best_decrease
            best_decrease <- delta
            best_vertex <- u
        else if delta > second_best_decrease
            second_best_decrease <- delta

    if best_decrease - second_best_decrease < MIN_AREA_DECREASE_EPSILON
        raise ambiguity error

    append H to hulls
    append best_vertex to peel_order
    append best_decrease to area_decreases
    active_points <- active_points \ {best_vertex}

return peel_order, area_decreases, hulls, active_points
```

## `V2` Layered Linked-List Implementation

`V2` maintains convex layers explicitly. Linear-time tangent and visible-chain
walks are acceptable. The key structural step is that a peel removes one node
from its layer in constant time and restores affected layers by splicing
contiguous chains upward rather than rebuilding whole layers as the primary
mechanism.

Sensitivity is computed from local geometry: if `u` has neighbors `t` and `v`
on the outer layer, and `A(u)` is the contiguous chain of active points on the
next layer, then

```text
sens(u) = area(poly(t o u o v o A(u)))
```

where `A(u)` is found using tangent queries from `t` and `v` to the next layer,
followed by a walk along that layer.

```text
Algorithm V2_LayeredLinkedWeightedPeeling(P)
Input:
    A set P of n points in the plane

L[1], L[2], ..., L[k] <- all convex layers of P
Represent each L[i] as a circular doubly linked list
Build point-to-node indices for all layer nodes

peel_order <- empty list
area_decreases <- empty list
hulls <- empty list
layers_after_peel <- empty list

while |P| > 3
    best_vertex <- null
    best_decrease <- -infinity
    second_best_decrease <- -infinity

    for each vertex u in L[1]
        t, v <- neighbors of u in L[1]
        A(u) <- active chain on L[2]
                found by tangent queries from t and v
                and a walk along L[2]
        delta <- area(poly(t o u o v o A(u)))

        if delta > best_decrease
            second_best_decrease <- best_decrease
            best_decrease <- delta
            best_vertex <- u
        else if delta > second_best_decrease
            second_best_decrease <- delta

    if best_decrease - second_best_decrease < MIN_AREA_DECREASE_EPSILON
        raise ambiguity error

    append canonical(L[1]) to hulls
    append best_vertex to peel_order
    append best_decrease to area_decreases

    Delete best_vertex from L[1] in O(1) time
    Delete best_vertex from the active point set

    i <- 1
    while i < number of nonempty layers
        Determine the contiguous chain C on L[i + 1] that must move to L[i]
        using tangent / visible-chain queries between the broken endpoints of L[i]

        if C is empty
            break

        Splice C out of L[i + 1]
        Splice C into L[i] between the appropriate boundary nodes

        if L[i + 1] becomes empty
            delete L[i + 1]
            break

        i <- i + 1

    Rebuild or refresh the affected point-to-node indices
    append canonical snapshots of all nonempty layers to layers_after_peel

return peel_order, area_decreases, hulls, layers_after_peel, remaining points
```

## `V3` Efficient Tangent-Query Layered Implementation

`V3` keeps the layered strategy from `V2` but changes the representation of
each maintained layer. Logarithmic-time tangent queries require a tree-based
representation of the cyclic vertex order rather than a plain linked list.

Each maintained layer should therefore support:

- tangent queries from an external point in `O(log n)`
- access to a vertex's successor / predecessor in `O(1)` via leaf links
- split / join or equivalent subtree updates for promoted chains
- efficient search by cyclic order inside the layer

This is the first version where the representation itself changes in order to
meet the asymptotic goal. In `V2`, promoted chains can be moved by direct
pointer splicing. In `V3`, the same logical update typically becomes:

- identify the promoted chain by logarithmic tangent queries,
- isolate the corresponding interval in the source layer by tree splits,
- remove or rebuild that interval inside the source tree,
- and insert the interval into the target layer by tree joins or equivalent
  balanced-tree restructuring.

```text
Algorithm V3_EfficientLayeredWeightedPeeling(P)
Input:
    A set P of n points in the plane

L[1], L[2], ..., L[k] <- all convex layers of P
Represent each L[i] as a balanced leaf-linked tree whose leaves are ordered
cyclically along the perimeter of the layer
Initialize point-to-leaf indices and any auxiliary search structure

Initialize all sensitivities for points on L[1]
Store them in a max-priority queue Q

while |P| > 3
    u <- Q.extractMax()

    if u is stale
        recompute sens(u) and reinsert if needed
        continue

    append current outer hull to output
    append sens(u) to output
    append u to peel order

    t, v <- neighbors of u on L[1]
    A(u) <- active chain on L[2]
            found by two logarithmic tangent queries
            and a walk over the chain

    Delete u from L[1] using the tree representation
    Delete u from the active set

    i <- 1
    while i < number of nonempty layers
        Determine the promoted chain C on L[i + 1]
        using logarithmic tangent queries between the broken endpoints of L[i]

        if C is empty
            break

        Isolate C in the tree for L[i + 1]
        by split operations or equivalent balanced-tree restructuring
        Remove C from the tree for L[i + 1]
        Insert C into the tree for L[i]
        between the appropriate boundary vertices
        while preserving leaf links and balance

        if L[i + 1] becomes empty
            delete L[i + 1]
            break

        i <- i + 1

    for each newly promoted point x
        compute sens(x)
        Q.insert(x, sens(x))

    Recompute the sensitivities of the two neighbors
    of the peeled point whose active sets may have changed
    Update their keys in Q

return peel order and the associated per-step outputs
```

## `V4` Dynamic-Hull Implementation

`V4` matches the full algorithmic picture from the publication: maintain the
first two outer layers explicitly and store all deeper points in a deletion-only
dynamic convex hull structure.

At this point, hull restoration of `L^2` is no longer done by scanning through
all deeper static layers. Instead, points are drawn from `D_CH` through extreme
point or tangent queries and deleted from `D_CH` as they become exposed.

```text
Algorithm V4_DynamicWeightedPeeling(P)
Input:
    A set P of n points in the plane

L^1, L^2 <- the first two convex layers of P
Q <- empty max-priority queue

for each point u in L^1
    Compute A(u) on L^2 using tangent queries from u's neighbors
    Compute sens(u) = area(poly(t o u o v o A(u)))
    Q.insert(u, sens(u))

D_CH <- dynamic convex hull structure on P \ (L^1 union L^2)

while |P| > 3
    u <- Q.extractMax()
    t, v <- neighbors of u in L^1
    A(u) <- active chain on L^2

    Delete u from L^1
    Move A(u) from L^2 to L^1

    Let a and b be the broken endpoints on L^2 created by removing A(u)
    Restore the missing chain of L^2 by repeated extreme-point queries into D_CH:
        query with line ab in the direction of u
        if a point z is found, add z to L^2 and delete z from D_CH
        recurse or iterate on the subproblems induced by za and zb
        stop when no further point is exposed

    for each newly promoted point x now on L^1
        Compute A(x) using tangent queries on L^2
        Compute sens(x)
        Q.insert(x, sens(x))

    Recompute sens(t) and sens(v)
    Update their keys in Q

return peel order and the associated per-step outputs
```

## Relationship Between Versions

- `V1` is the brute-force correctness oracle.
- `V2` introduces explicit convex-layer maintenance with linked-list splicing and
  linear-time tangent queries.
- `V3` replaces the linked-list layer representation with leaf-linked balanced
  trees so tangent queries become logarithmic-time and chain moves become tree
  update operations rather than simple pointer splices.
- `V4` replaces the deeper static-layer view with a deletion-only dynamic convex
  hull engine and matches the full publication architecture.
