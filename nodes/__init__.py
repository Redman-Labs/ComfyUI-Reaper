"""Registration for all independently discoverable Reaper nodes."""
from .face_utilities import NODE_CLASSES as FACE_NODES
from .flow_utilities import NODE_CLASSES as FLOW_NODES
from .image_utilities import NODE_CLASSES as IMAGE_NODES
from .in_out_painting_utilities import NODE_CLASSES as IN_OUT_PAINTING_NODES
from .krea2_utilities import NODE_CLASSES as KREA2_NODES
from .latent_utilities import NODE_CLASSES as LATENT_NODES
from .mask_utilities import NODE_CLASSES as MASK_NODES
from .model_utilities import NODE_CLASSES as MODEL_NODES
from .pass_throughs import NODE_CLASSES as PASS_THROUGH_NODES
from .prompt_text_utilities import NODE_CLASSES as PROMPT_TEXT_NODES
from .switch_utilities import NODE_CLASSES as SWITCH_NODES
from .utilities import NODE_CLASSES as UTILITY_NODES
from .vae_utilities import NODE_CLASSES as VAE_NODES
from ._helpers._types import CropInfo

ALL_REAPER_NODES = [
    *FACE_NODES,
    *FLOW_NODES,
    *IMAGE_NODES,
    *IN_OUT_PAINTING_NODES,
    *KREA2_NODES,
    *LATENT_NODES,
    *MASK_NODES,
    *MODEL_NODES,
    *PASS_THROUGH_NODES,
    *PROMPT_TEXT_NODES,
    *SWITCH_NODES,
    *UTILITY_NODES,
    *VAE_NODES,
]

__all__ = ["ALL_REAPER_NODES", "CropInfo"]
