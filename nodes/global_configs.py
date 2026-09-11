"""User-editable settings shared by every Reaper node."""

# Change this value to update the branded suffix on every Reaper node title.
GLOBAL_NAME = "(Reaper)"

CATEGORIES = {
    "face_utilities": "Reaper/Face Utils",
    "flow_utilities": "Reaper/Flow Control",
    "image_utilities": "Reaper/Image Utils",
    "in_out_painting_utilities": "Reaper/In-Outpainting Utils",
    "krea2_utilities": "Reaper/Krea2 Utils",
    "latent_utilities": "Reaper/Latent Utils",
    "mask_utilities": "Reaper/Mask Utils",
    "model_utilities": "Reaper/Model Utils",
    "pass_throughs": "Reaper/Pass Throughs",
    "prompt_text_utilities": "Reaper/Prompt & Text",
    "switch_utilities": "Reaper/Switches",
    "vae_utilities": "Reaper/VAE Utils",
    "utilities": "Reaper/Tools",
}

def node_title(title: str, *, branded: bool = True) -> str:
    suffix = GLOBAL_NAME.strip()
    return f"{title} {suffix}".strip() if branded and suffix else title

def configure_node(base_class, category_key: str, title: str, *, branded: bool = True):
    """Create a configured public node class without changing its stable node ID."""
    class ConfiguredNode(base_class):
        @classmethod
        def define_schema(cls):
            schema = super().define_schema()
            schema.category = CATEGORIES[category_key]
            schema.display_name = node_title(title, branded=branded)
            return schema
    ConfiguredNode.__name__ = base_class.__name__
    ConfiguredNode.__qualname__ = base_class.__qualname__
    ConfiguredNode.__module__ = base_class.__module__
    return ConfiguredNode

__all__ = ["GLOBAL_NAME", "CATEGORIES", "node_title", "configure_node"]
