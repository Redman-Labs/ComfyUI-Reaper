from comfy_api.latest import io


# Shared socket type for crop metadata. Future Reaper uncrop or
# restoration nodes should import and use this exact object/type ID.
CropInfo = io.Custom("CROP_INFO")
