"""Property-based tests: the business rules must hold for any acyclic recipe graph (NFR-01)."""

from hypothesis import given, settings
from hypothesis import strategies as st

from allergen_engine.graph import CycleError, topological_order, would_create_cycle
from allergen_engine.model import Allergen, EquipmentNode, IngredientNode, RecipeNode, Status, Summary
from allergen_engine.policy import merge, pending_removals
from allergen_engine.propagation import declare_all
from allergen_engine.repository import InMemoryRepository

allergen_sets = st.frozensets(st.sampled_from(list(Allergen)), max_size=4)


@st.composite
def kitchens(draw):
    """Random ingredients and an acyclic recipe graph (a recipe only uses recipes with smaller ids)."""
    n_ing = draw(st.integers(1, 8))
    ingredients = {}
    for i in range(n_ing):
        contains = draw(allergen_sets)
        may = draw(allergen_sets) - contains  # an ingredient never has both (form validation)
        ingredients[i] = IngredientNode(i, f"I{i}", contains, may, draw(st.booleans()))
    equipment = {
        e: EquipmentNode(e, f"E{e}", draw(st.booleans())) for e in range(1000, 1000 + draw(st.integers(0, 3)))
    }
    recipes = {}
    for r in range(100, 100 + draw(st.integers(1, 8))):
        parts = draw(st.lists(st.integers(0, n_ing - 1), max_size=4, unique=True))
        subs = draw(st.lists(st.sampled_from(sorted(recipes)), max_size=3, unique=True)) if recipes else []
        tools = (
            draw(st.lists(st.sampled_from(sorted(equipment)), max_size=2, unique=True)) if equipment else []
        )
        recipes[r] = RecipeNode(r, f"R{r}", tuple(parts), tuple(subs), tuple(tools))
    return InMemoryRepository(ingredients, recipes, equipment)


def has_empty_recipe(repo, rid):
    recipe = repo.recipes()[rid]
    if not recipe.ingredient_ids and not recipe.recipe_ids:
        return True
    return any(has_empty_recipe(repo, sid) for sid in recipe.recipe_ids)


def leaf_ingredients(repo, rid):
    recipe = repo.recipes()[rid]
    found = {repo.ingredients()[i] for i in recipe.ingredient_ids}
    for sid in recipe.recipe_ids:
        found |= leaf_ingredients(repo, sid)
    return found


@settings(max_examples=300)
@given(kitchens())
def test_declaration_matches_all_ingredients_at_any_depth(repo):
    """BR-1, BR-2, BR-4 checked against a naive recursive reference calculation."""
    declarations = declare_all(repo)
    for rid, declaration in declarations.items():
        leaves = leaf_ingredients(repo, rid)
        contained = set().union(*(i.contains for i in leaves))
        traces = set().union(*(i.may_contain for i in leaves)) - contained
        assert set(declaration.contains) == contained
        assert set(declaration.may_contain) == traces
        assert not set(declaration.contains) & set(declaration.may_contain)
        assert declaration.needs_staff == (any(not i.known for i in leaves) or has_empty_recipe(repo, rid))
        for allergen in Allergen:
            if declaration.status(allergen) is Status.FREE:
                assert not has_empty_recipe(repo, rid)
                assert all(i.known and allergen not in i.contains | i.may_contain for i in leaves)


@given(kitchens())
def test_every_path_ends_in_an_ingredient_that_explains_it(repo):
    names = {i.name: i for i in repo.ingredients().values()}
    for declaration in declare_all(repo).values():
        for allergen, paths in declaration.contains.items():
            assert paths and all(allergen in names[p[-1]].contains for p in paths)
        for paths in declaration.may_contain.values():
            assert paths and all(names[p[-1]].name == p[-1] for p in paths)


@given(kitchens())
def test_sub_recipes_never_declare_more_than_the_recipes_using_them(repo):
    """BR-1 monotonicity: adding a recipe as a part can only add allergens, never remove them."""
    declarations = declare_all(repo)
    for rid, recipe in repo.recipes().items():
        for sid in recipe.recipe_ids:
            assert set(declarations[sid].contains) <= set(declarations[rid].contains)
            assert declarations[sid].needs_staff <= declarations[rid].needs_staff


@given(st.dictionaries(st.integers(0, 6), st.lists(st.integers(0, 6), max_size=3), max_size=7))
def test_topological_order_or_cycle(edges):
    """BR-5: either an order where every sub-recipe comes first, or a real cycle is reported."""
    try:
        order = topological_order(edges)
    except CycleError as error:
        cycle = error.cycle
        assert cycle[0] == cycle[-1]
        assert all(b in edges.get(a, ()) for a, b in zip(cycle, cycle[1:], strict=False))
        return
    position = {node: i for i, node in enumerate(order)}
    for parent, children in edges.items():
        for child in children:
            assert position[child] < position[parent]


@given(
    st.dictionaries(st.integers(0, 6), st.lists(st.integers(0, 6), max_size=3), max_size=7),
    st.integers(0, 6),
    st.integers(0, 6),
)
def test_would_create_cycle_agrees_with_topological_order(edges, recipe, sub):
    try:
        topological_order(edges)
    except CycleError:
        return  # only acyclic graphs are ever stored
    extended = {**edges, recipe: [*edges.get(recipe, ()), sub]}
    try:
        topological_order(extended)
        creates = False
    except CycleError:
        creates = True
    assert would_create_cycle(edges, recipe, sub) == creates


def contained(repo, rid):
    return set().union(*(i.contains for i in leaf_ingredients(repo, rid)))


def cross_reference(repo, rid):
    """Naive BR-3: allergens of other recipes on shared, non-dedicated equipment, also through sub-recipes."""
    recipe = repo.recipes()[rid]
    found = set()
    for eid in recipe.equipment_ids:
        if not repo.equipment()[eid].dedicated:
            for other in repo.recipes().values():
                if other.id != rid and eid in other.equipment_ids:
                    found |= contained(repo, other.id)
    for sid in recipe.recipe_ids:
        found |= cross_reference(repo, sid)
    return found


@settings(max_examples=300)
@given(kitchens())
def test_cross_contact_matches_reference(repo):
    for rid, declaration in declare_all(repo).items():
        assert set(declaration.cross_contact) == cross_reference(repo, rid) - contained(repo, rid)
        for allergen, paths in declaration.cross_contact.items():
            assert paths and declaration.status(allergen) is Status.MAY_CONTAIN


summaries = st.builds(
    lambda contains, may, ask: Summary(contains, may - contains, ask),
    allergen_sets,
    allergen_sets,
    st.booleans(),
)


@given(st.one_of(st.none(), summaries), summaries)
def test_br6_published_never_says_less_than_calculated_or_previously_published(published, calculated):
    merged = merge(published, calculated)
    assert not merged.contains & merged.may_contain
    for allergen in Allergen:
        assert merged.rank(allergen) == max(
            calculated.rank(allergen), published.rank(allergen) if published else 0
        )
    assert merged.ask_staff >= calculated.ask_staff
    weaker, ask_dropped = pending_removals(merged, calculated)
    assert all(merged.rank(a) > calculated.rank(a) for a in weaker)
    assert not ask_dropped or (merged.ask_staff and not calculated.ask_staff)
    if published is None:
        assert (weaker, ask_dropped) == (frozenset(), False)  # nothing to approve for a new recipe
