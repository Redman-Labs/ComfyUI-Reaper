"""Reusable implementation shared by nodes in this category."""
from __future__ import annotations

from ...global_configs import CATEGORIES

CATEGORY = CATEGORIES['face_utilities']
_CATEGORY = CATEGORY

"""Face Tools nodes for the Reaper ComfyUI extension.

Includes face detection, filtering, cropping, parsing, and person-mask tools.
"""

from functools import lru_cache

import numpy as np

import torch

import torchvision as tv

from comfy_api.latest import io

from ..._helpers.face_tools import detect_faces, mask_BiSeNet, mask_crop, mask_jonathandinu, mask_types

import os

import urllib.request

from functools import reduce

import cv2

import folder_paths

import mediapipe as mp

FaceCollection = io.Custom("FACE")

FaceWarp = io.Custom("WARP")

def _toggle(name: str, label: str, default: bool, tooltip: str):
    return io.Boolean.Input(
        name,
        display_name=label,
        default=default,
        label_on="Enabled",
        label_off="Disabled",
        tooltip=tooltip,
    )

def _gender_classifier():
    from transformers import pipeline

    return pipeline(
        "image-classification",
        model="dima806/man_woman_face_image_detection",
        device=0 if torch.cuda.is_available() else -1,
    )

def _classify_face(face, classifier) -> str:
    """Return the classifier's normalized label for one FACE object."""
    _warp, crop = face.crop(224, 1.2)
    tensor = crop[0].permute(2, 0, 1)
    tensor = tv.transforms.functional.resize(tensor, (224, 224), antialias=True)
    predictions = classifier(tv.transforms.functional.to_pil_image(tensor.clamp(0, 1)))
    return str(max(predictions, key=lambda item: item["score"])["label"]).lower()

_PARTS = [
    ("skin", "Skin", True, "Facial skin region."),
    ("left_brow", "Left Brow", True, "Left eyebrow region from the viewer-facing parsing map."),
    ("right_brow", "Right Brow", True, "Right eyebrow region from the viewer-facing parsing map."),
    ("left_eye", "Left Eye", True, "Left eye region."),
    ("right_eye", "Right Eye", True, "Right eye region."),
    ("eyeglasses", "Eyeglasses", True, "Glasses and eyeglass-frame region."),
    ("left_ear", "Left Ear", True, "Left ear region."),
    ("right_ear", "Right Ear", True, "Right ear region."),
    ("earring", "Earring", True, "Earrings and related ear accessories."),
    ("nose", "Nose", True, "Nose region."),
    ("mouth", "Mouth", True, "Interior mouth region excluding separately labelled lips."),
    ("upper_lip", "Upper Lip", True, "Upper-lip region."),
    ("lower_lip", "Lower Lip", True, "Lower-lip region."),
    ("neck", "Neck", False, "Visible neck skin."),
    ("necklace", "Necklace", False, "Necklace and neck-accessory region."),
    ("cloth", "Clothing", False, "Clothing region visible in the crop."),
    ("hair", "Hair", False, "Hair region."),
    ("hat", "Hat", False, "Hat and headwear region."),
]

def _mask_inputs(default_overrides: dict[str, bool] | None = None):
    overrides = default_overrides or {}
    return [
        io.Image.Input("crop", display_name="Face Crops", tooltip="Aligned face-crop IMAGE batch, normally from Crop Faces."),
        *[
            _toggle(name, label, overrides.get(name, default), tooltip + " Enabled regions are combined into one mask.")
            for name, label, default, tooltip in _PARTS
        ],
    ]

def _part_kwargs(parts: dict) -> dict:
    """Translate descriptive V3 input names to the source parser argument names."""
    return {
        "skin": parts["skin"],
        "l_brow": parts["left_brow"],
        "r_brow": parts["right_brow"],
        "l_eye": parts["left_eye"],
        "r_eye": parts["right_eye"],
        "eye_g": parts["eyeglasses"],
        "l_ear": parts["left_ear"],
        "r_ear": parts["right_ear"],
        "ear_r": parts["earring"],
        "nose": parts["nose"],
        "mouth": parts["mouth"],
        "u_lip": parts["upper_lip"],
        "l_lip": parts["lower_lip"],
        "neck": parts["neck"],
        "neck_l": parts["necklace"],
        "cloth": parts["cloth"],
        "hair": parts["hair"],
        "hat": parts["hat"],
    }

_MODEL_DIRECTORY = os.path.join(folder_paths.models_dir, "mediapipe")

_SEGMENTER_MODEL = "selfie_multiclass_256x256.tflite"

_LANDMARKER_MODEL = "face_landmarker.task"

_MODEL_URLS = {
    _SEGMENTER_MODEL: (
        "https://storage.googleapis.com/mediapipe-models/image_segmenter/"
        "selfie_multiclass_256x256/float32/latest/"
        + _SEGMENTER_MODEL
    ),
    _LANDMARKER_MODEL: (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
        "face_landmarker/float16/1/"
        + _LANDMARKER_MODEL
    ),
}

_FACE_REGIONS = {
    "face": [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397,
             365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58,
             132, 93, 234, 127, 162, 21, 54, 103, 67, 109],
    "left_eyebrow": [336, 296, 334, 293, 300, 276, 283, 282, 295, 285],
    "right_eyebrow": [70, 63, 105, 66, 107, 55, 65, 52, 53, 46],
    "left_eye": [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387,
                 386, 385, 384, 398],
    "right_eye": [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158,
                  159, 160, 161, 246],
    "left_pupil": [474, 475, 476, 477],
    "right_pupil": [469, 470, 471, 472],
    "lips": [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324,
             318, 402, 317, 14, 87, 178, 88, 95, 78],
}

def _model_path(name: str) -> str:
    """Return a model path, downloading the official asset when absent."""
    path = os.path.join(_MODEL_DIRECTORY, name)
    if os.path.isfile(path):
        return path
    os.makedirs(_MODEL_DIRECTORY, exist_ok=True)
    temporary = path + ".download"
    try:
        print(f"[Reaper] Downloading MediaPipe model: {name}")
        urllib.request.urlretrieve(_MODEL_URLS[name], temporary)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
    return path

def _mp_image(rgb: np.ndarray) -> mp.Image:
    return mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=np.ascontiguousarray(rgb, dtype=np.uint8),
    )

def _bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.nonzero(mask > 0)
    if xs.size == 0:
        return None
    left, right = int(xs.min()), int(xs.max()) + 1
    top, bottom = int(ys.min()), int(ys.max()) + 1
    pad_x = round((right - left) * 0.2)
    pad_y = round((bottom - top) * 0.2)
    height, width = mask.shape
    return (
        max(0, left - pad_x),
        max(0, top - pad_y),
        min(width, right + pad_x),
        min(height, bottom + pad_y),
    )

def _segment(
    segmenter,
    rgb: np.ndarray,
    classes: list[int],
    confidence: float,
    refine: bool,
) -> np.ndarray:
    if not classes:
        return np.zeros(rgb.shape[:2], dtype=np.float32)
    result = segmenter.segment(_mp_image(rgb))
    masks = [result.confidence_masks[index].numpy_view().squeeze() for index in classes]
    mask = reduce(np.maximum, masks)
    mask = (mask > confidence).astype(np.float32)
    if refine:
        bounds = _bbox(mask)
        if bounds is not None:
            left, top, right, bottom = bounds
            crop = _segment(
                segmenter,
                rgb[top:bottom, left:right],
                classes,
                confidence,
                False,
            )
            mask.fill(0)
            mask[top:bottom, left:right] = crop
    return mask

def _landmarks(
    landmarker,
    rgb: np.ndarray,
    enabled_regions: list[str],
) -> np.ndarray:
    mask = np.zeros(rgb.shape[:2], dtype=np.uint8)
    if not enabled_regions:
        return mask.astype(np.float32)
    height, width = mask.shape
    result = landmarker.detect(_mp_image(rgb))
    for face in result.face_landmarks:
        points = np.asarray(
            [(round(point.x * width), round(point.y * height)) for point in face],
            dtype=np.int32,
        )
        for region in enabled_regions:
            cv2.fillPoly(mask, [points[_FACE_REGIONS[region]]], 255)
    return mask.astype(np.float32) / 255.0

__all__ = [name for name in globals() if not name.startswith("__")]
