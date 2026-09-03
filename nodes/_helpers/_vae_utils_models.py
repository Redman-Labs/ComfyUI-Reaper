"""Small bundled neural models used by the Reaper VAE utility nodes."""

from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

import comfy.utils


MODEL_DIRECTORY = Path(__file__).resolve().parent.parent / "models" / "vae_utils"


def _load_state_dict(filename: str) -> dict[str, torch.Tensor]:
    path = MODEL_DIRECTORY / filename
    if not path.is_file():
        raise FileNotFoundError(
            f"The bundled Reaper VAE model is missing: {path}"
        )
    return comfy.utils.load_torch_file(str(path), safe_load=True)


class LayerNorm3d(nn.LayerNorm):
    def __init__(self, num_channels: int, eps: float = 1e-6) -> None:
        super().__init__(num_channels, eps=eps, elementwise_affine=False)

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        tensor = tensor.permute(0, 2, 3, 4, 1)
        tensor = F.layer_norm(
            tensor,
            self.normalized_shape,
            self.weight,
            self.bias,
            self.eps,
        )
        return tensor.permute(0, 4, 1, 2, 3)


class DiCoBlock3d(nn.Module):
    def __init__(
        self,
        hidden_size: int,
        mlp_ratio: float = 4.0,
        kernel_size: int = 3,
    ) -> None:
        super().__init__()
        # Attribute names are part of the bundled state-dict format.
        self.conv2 = nn.Conv3d(
            hidden_size,
            hidden_size,
            kernel_size=(1, kernel_size, kernel_size),
            padding=(0, kernel_size // 2, kernel_size // 2),
            padding_mode="replicate",
        )
        self.conv3 = nn.Conv3d(hidden_size, hidden_size, kernel_size=1)
        self.cca = nn.Sequential(
            nn.AdaptiveAvgPool3d(1),
            nn.Conv3d(hidden_size, hidden_size, kernel_size=1),
            nn.Sigmoid(),
        )
        feed_forward_channels = int(mlp_ratio * hidden_size)
        self.conv4 = nn.Conv3d(
            hidden_size,
            feed_forward_channels,
            kernel_size=1,
        )
        self.conv5 = nn.Conv3d(
            feed_forward_channels,
            hidden_size,
            kernel_size=1,
        )
        self.norm1 = LayerNorm3d(hidden_size)
        self.norm2 = LayerNorm3d(hidden_size)

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        hidden = self.norm1(tensor)
        hidden = F.gelu(self.conv2(hidden))
        hidden = self.conv3(hidden * self.cca(hidden))
        hidden = tensor + hidden

        feed_forward = self.norm2(hidden)
        feed_forward = self.conv5(F.gelu(self.conv4(feed_forward)))
        return hidden + feed_forward


class WanLatentUpscale2xModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        hidden_size = 128
        self.upscale = 2
        self.conv_in = nn.Conv3d(
            16,
            hidden_size,
            kernel_size=(1, 3, 3),
            padding=(0, 1, 1),
            padding_mode="replicate",
        )
        self.blocks = nn.ModuleList(
            [DiCoBlock3d(hidden_size) for _ in range(8)]
        )
        self.conv_out = nn.Conv3d(
            hidden_size,
            16 * self.upscale**2,
            kernel_size=(1, 3, 3),
            padding=(0, 1, 1),
            padding_mode="replicate",
        )

    def forward(self, tensor: torch.Tensor) -> torch.Tensor:
        hidden = self.conv_in(tensor)
        for block in self.blocks:
            hidden = block(hidden)
        output = self.conv_out(hidden)
        output = F.pixel_shuffle(
            output.movedim(1, 2), self.upscale
        ).movedim(2, 1)
        residual = F.interpolate(
            tensor,
            scale_factor=(1, self.upscale, self.upscale),
            mode="nearest-exact",
        )
        return output + residual


class WanLatentProjector(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.scale_t = 4
        self.scale_s = 8
        self.projections = nn.ModuleList(
            [
                nn.Linear(16, 3 * self.scale_s**2),
                nn.Linear(16, 3 * self.scale_t * self.scale_s**2),
                nn.Linear(16, 3 * self.scale_t * self.scale_s**2),
            ]
        )

    def forward(self, latents: torch.Tensor) -> torch.Tensor:
        frames = []
        for frame_index in range(latents.shape[2]):
            projection_index = min(frame_index, len(self.projections) - 1)
            features = self.projections[projection_index](
                latents[:, :, frame_index].movedim(1, -1)
            ).movedim(-1, 1)
            features = F.pixel_shuffle(features, self.scale_s).unsqueeze(2)
            if frame_index == 0:
                frames.append(features)
            else:
                frames.extend(features.chunk(self.scale_t, dim=1))
        return torch.cat(frames, dim=2)


LATENT_UPSCALE_MODELS = ["Wan 2.1 latent upscale 2x"]


def load_latent_upscale_model(name: str) -> WanLatentUpscale2xModel:
    if name not in LATENT_UPSCALE_MODELS:
        raise ValueError(f"Unsupported latent upscale model: {name}")
    model = WanLatentUpscale2xModel()
    model.load_state_dict(
        _load_state_dict("wan21_latent_upscale_2x.safetensors")
    )
    model.eval()
    return model


def load_wan_latent_projector() -> WanLatentProjector:
    model = WanLatentProjector()
    model.load_state_dict(
        _load_state_dict("wan21_latent_projector.safetensors")
    )
    model.eval()
    return model


__all__ = [
    "LATENT_UPSCALE_MODELS",
    "load_latent_upscale_model",
    "load_wan_latent_projector",
]
