from typing import Optional, List, Tuple

from PIL import Image

from .server.models import V1EnvState
from .img import convert_images


class EnvState:
    """The state of the environment"""

    def __init__(
        self,
        images: Optional[List[str | Image.Image]] = None,
        coordinates: Optional[Tuple[int, int]] = None,
        video: Optional[str] = None,
        text: Optional[str] = None,
    ) -> None:
        self.images = convert_images(images) if images else None  # type: ignore
        self.coordinates = coordinates
        self.video = video
        self.text = text

    def to_v1(self) -> V1EnvState:
        return V1EnvState(
            images=self.images,
            coordinates=self.coordinates,
            video=self.video,
            text=self.text,
        )

    @classmethod
    def from_v1(cls, data: V1EnvState) -> "EnvState":
        out = cls.__new__(cls)
        out.images = convert_images(data.images) if data.images else None
        out.coordinates = data.coordinates
        out.video = data.video
        out.text = data.text

        return out