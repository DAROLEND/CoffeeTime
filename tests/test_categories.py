"""Verifies the canonical ProductCategory enum (Phase 0 output) matches
every category-table name actually used across the PHP codebase, and that
every category resolves to a concrete SQLAlchemy model."""
from app.constants.categories import CATEGORY_MODEL_MAP, ProductCategory

# Exact set confirmed via:
#   grep -rn "coffee_items\|fast_food_items\|...' --include=*.php .
# across forms/, pages/, admin/, includes/telegram.php, db/get_menu_items.php.
EXPECTED_TABLE_NAMES = {
    "coffee_items", "cold_drink_items", "dessert_items", "fast_food_items",
    "pizza_items", "mini_pizza_items", "ice_cream_items", "cake_items",
    "sushi_items", "sushi_sets", "salad_items", "sauces",
}


def test_enum_values_match_actual_table_names():
    assert {c.value for c in ProductCategory} == EXPECTED_TABLE_NAMES


def test_every_category_has_a_model():
    for category in ProductCategory:
        model = CATEGORY_MODEL_MAP.get(category)
        assert model is not None, f"no model registered for {category}"
        assert model.__tablename__ == category.value
