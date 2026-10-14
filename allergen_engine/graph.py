"""The recipe graph: recipes point to their sub-recipes and must never form a cycle (BR-5)."""

from collections.abc import Iterable, Mapping

Edges = Mapping[int, Iterable[int]]  # recipe id -> ids of its sub-recipes


class CycleError(ValueError):
    def __init__(self, cycle: list[int]):
        super().__init__(f"recipe cycle: {' -> '.join(map(str, cycle))}")
        self.cycle = cycle


def topological_order(edges: Edges) -> list[int]:
    """All recipe ids, sub-recipes before the recipes that use them. Raises CycleError."""
    order: list[int] = []
    state: dict[int, str] = {}  # "open" while on the current path, "done" when finished
    for root in edges:
        if root in state:
            continue
        stack = [(root, iter(edges.get(root, ())))]
        state[root] = "open"
        while stack:
            node, children = stack[-1]
            child = next(children, None)
            if child is None:
                stack.pop()
                state[node] = "done"
                order.append(node)
            elif state.get(child) == "open":
                path = [n for n, _ in stack]
                raise CycleError(path[path.index(child) :] + [child])
            elif child not in state:
                state[child] = "open"
                stack.append((child, iter(edges.get(child, ()))))
    return order


def would_create_cycle(edges: Edges, recipe_id: int, new_sub_recipe_id: int) -> bool:
    """True if adding new_sub_recipe_id as a part of recipe_id would close a cycle."""
    seen, todo = set(), [new_sub_recipe_id]
    while todo:
        node = todo.pop()
        if node == recipe_id:
            return True
        if node not in seen:
            seen.add(node)
            todo.extend(edges.get(node, ()))
    return False
