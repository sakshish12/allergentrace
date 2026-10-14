# Business rules of the allergen calculation

These rules define how AllergenTrace derives the declaration of a dish. They are implemented in the module `allergen_engine` and each rule has its own automated tests.

| ID | Rule |
|---|---|
| BR-1 Propagation | A recipe contains every allergen that one of its components (ingredient or sub-recipe) contains. The same holds for "may contain". |
| BR-2 Priority | "Contains" overrides "may contain" for the same allergen. |
| BR-3 Cross-contact | If two recipes use the same non-dedicated equipment, each receives the allergens contained in the other as "may contain". |
| BR-4 Unknown data | If any component has the status "unknown" for an allergen, the dish shows "please ask staff" for it and is never listed as free of that allergen. |
| BR-5 No cycles | Recipes form a directed acyclic graph; an edit that creates a cycle is rejected. |
| BR-6 Fail-safe publication | The published declaration may contain more allergens than the calculated one, but never fewer. Additions are published at once, removals only after owner approval. |

Order of precedence for one allergen in one dish: contains > unknown ("please ask staff") > may contain > free.
