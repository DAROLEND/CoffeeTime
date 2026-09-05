"""
Single source of truth for the "which of the 11 product tables (+ sauces)
does this order_items.category / cart-line category string refer to"
question.

The PHP codebase re-declared this whitelist ad hoc in ~15 different files
(forms/*.php, pages/*.php, admin/*.php, includes/telegram.php), with
slightly inconsistent membership between them (verified during Phase 0:
`grep -rn "coffee_items\\|fast_food_items\\|..." --include=*.php .`).
Every one of those PHP whitelists used the *literal MySQL table name* as
the category string, and `order_items.category` in the live data
(CoffeeTime.sql) stores exactly those table names — e.g.
`INSERT INTO order_items ... VALUES (13,22,2,1,210.00,'pizza_items',...)`.

So the enum values below are fixed to the exact existing table names,
byte-for-byte, to guarantee zero drift against historical order_items
rows and zero re-mapping needed on data import.
"""
from __future__ import annotations

from enum import Enum


class ProductCategory(str, Enum):
    COFFEE = "coffee_items"
    COLD_DRINK = "cold_drink_items"
    DESSERT = "dessert_items"
    FAST_FOOD = "fast_food_items"
    PIZZA = "pizza_items"
    MINI_PIZZA = "mini_pizza_items"
    ICE_CREAM = "ice_cream_items"
    CAKE = "cake_items"
    SUSHI = "sushi_items"
    SUSHI_SET = "sushi_sets"
    SALAD = "salad_items"
    SAUCE = "sauces"  # the only category that is also independently browsable/orderable,
    # not just a pizza/fast-food add-on (forms/add_to_cart.php:128 `$table === 'sauces'` branch)


# Categories that support a small/large size choice + optional cheese-crust
# add-on (pizza_items, mini_pizza_items) or a size-driven prep-time estimate
# (sushi_sets) — mirrors the `$sizedCats`/`$sizedCategories` arrays repeated
# in admin/orders.php, admin/view_order.php, admin/get_order_details.php.
SIZED_CATEGORIES: frozenset[ProductCategory] = frozenset(
    {ProductCategory.PIZZA, ProductCategory.MINI_PIZZA, ProductCategory.SUSHI_SET}
)

# Only pizza_items carries the cheese-crust surcharge (mini_pizza_items does
# not — confirmed in forms/add_to_cart.php: the +65/+100 crust branch is
# nested inside the pizza_items-only price-recompute block, mini_pizza_items
# shares the size lookup but never applies a crust surcharge).
CHEESE_CRUST_CATEGORIES: frozenset[ProductCategory] = frozenset({ProductCategory.PIZZA})

CHEESE_CRUST_SURCHARGE = {"small": 65, "large": 100}


def _model_map() -> dict[ProductCategory, type]:
    # Imported lazily (function, not module-level) to avoid a circular import
    # between app.constants.categories and app.models.catalog.
    from app.models import catalog as m

    return {
        ProductCategory.COFFEE: m.CoffeeItem,
        ProductCategory.COLD_DRINK: m.ColdDrinkItem,
        ProductCategory.DESSERT: m.DessertItem,
        ProductCategory.FAST_FOOD: m.FastFoodItem,
        ProductCategory.PIZZA: m.PizzaItem,
        ProductCategory.MINI_PIZZA: m.MiniPizzaItem,
        ProductCategory.ICE_CREAM: m.IceCreamItem,
        ProductCategory.CAKE: m.CakeItem,
        ProductCategory.SUSHI: m.SushiItem,
        ProductCategory.SUSHI_SET: m.SushiSet,
        ProductCategory.SALAD: m.SaladItem,
        ProductCategory.SAUCE: m.Sauce,
    }


class _CategoryModelMap:
    """Lazily-built, then cached, category -> SQLAlchemy model class map.

    Replaces the ~15 ad-hoc `if ($category === 'pizza_items') { ... }` /
    dynamic `` `$category` `` table-name interpolation blocks scattered
    across the PHP codebase with one lookup used everywhere (cart
    resolution, checkout, order rendering, admin product CRUD).
    """

    _map: dict[ProductCategory, type] | None = None

    def _ensure(self) -> dict[ProductCategory, type]:
        if self._map is None:
            self._map = _model_map()
        return self._map

    def __getitem__(self, category: ProductCategory) -> type:
        return self._ensure()[category]

    def get(self, category: ProductCategory) -> type | None:
        return self._ensure().get(category)

    def items(self):
        return self._ensure().items()


CATEGORY_MODEL_MAP = _CategoryModelMap()
