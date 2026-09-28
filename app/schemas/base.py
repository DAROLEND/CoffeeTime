from pydantic import BaseModel, ConfigDict


class Schema(BaseModel):
    """Base for every API model.

    In responses a field with a default is always present, so the OpenAPI
    *output* schema marks it required; request schemas keep defaulted
    fields optional. That gives the generated TypeScript types exact
    shapes in both directions (FastAPI emits separate -Input/-Output
    schemas where they differ).
    """

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)
