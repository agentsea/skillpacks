from typing import Tuple, Optional, List

from pydantic import BaseModel, Field
from PIL import Image, ImageDraw
from agentdesk import Desktop


class ClickTarget(BaseModel):
    """A click target"""

    description: str = Field(description="The target description e.g. 'a blue login button'")
    location: str = Field(description="The target location e.g. top-right, center-left")
    text: Optional[str] = Field(description="The target text, if present e.g. 'Login'")
    puropose: str = Field(description="The target purpose e.g. 'log the user in'")
    expectation: str = Field(description="The target expectation e.g. 'a login page will open'")


class FoundTarget(BaseModel):
    """A found click target"""

    target: ClickTarget
    bbox: Tuple[int, int, int, int]


class State:
    """An environment state"""

    def __init__(self, screenshot: Image.Image, found_targets: List[FoundTarget]):
        self.screenshot = screenshot
        self.found_targets = found_targets

    def draw_found(self) -> Image.Image:
        """Draws the found targets on the screenshot"""
        # Make a copy of the screenshot to draw on
        image_copy = self.screenshot.copy()
        draw = ImageDraw.Draw(image_copy)

        for found_target in self.found_targets:
            # Draw the bounding box
            bbox = found_target.bbox
            draw.rectangle(bbox, outline="red", width=3)

            # Optionally, add a label near the bounding box
            label = found_target.target.description
            text_position = (bbox[0], bbox[1] - 10)  # Position text above the bbox
            draw.text(text_position, label, fill="red")

        return image_copy


def find_state(screenshot: Image.Image) -> Tuple[int, int]:
    pass

def find_target(desktop: Desktop) -> ClickTarget:
    pass

def find_with_ocr(text: str) -> Tuple[int, int]:
    pass

def find_with_dots(target: ClickTarget) -> Tuple[int, int]:
    pass

def find_center_bbox(bbox: Tuple[int, int, int, int]) -> Tuple[int, int]:
    pass

def verify_click(desktop: Desktop, target: ClickTarget):
    pass

def save_click(desktop: Desktop, target: ClickTarget):
    pass

def bbox_from_point(point: Tuple[int, int]) -> Tuple[int, int, int, int]:
    pass

def run(desktop: Desktop, base_url: str):
    desktop.open_url(base_url)

    target = find_target(desktop)

    if target.text:
        point = find_with_ocr(target.text)
    else:
        point = find_with_dots(target)
    
    bbox = bbox_from_point(point)
    center = find_center_bbox(bbox)

    desktop.click(x=center[0], y=center[1])

    # how do we know what is supposed to happen?
    verify_click(desktop, target)

    save_click(desktop, target)
    

if __name__ == "__main__":
    pass