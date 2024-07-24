# This code is based on the revised code from fastchat based on tatsu-lab/stanford_alpaca.
import json
import os
import random
import string
import sys
import uuid
from typing import List
import json
import time
from typing import List
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


import torch
from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed

import base64
import json
import os
import re
import time
from io import BytesIO
from typing import List

from agentdesk import Desktop
from mllm import RoleThread, Router
from PIL import Image
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up basic logging configuration
logging.basicConfig(
    level=logging.INFO,
    filename="mouse_coords.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)
mllm_logger = logging.getLogger("mllm.router")
mllm_logger.setLevel(logging.DEBUG)


def extract_json(input_str: str) -> str:
    """
    Extracts and parses a JSON object from the input string using regex if it is tagged with 'json\n'
    and enclosed in backticks, otherwise returns the input string.

    :param input_str: A string that may contain a JSON object.
    :return: A dictionary if JSON is parsed, otherwise the original string.
    """
    # Regex to match 'json\n{...}' pattern enclosed in backticks
    match = re.search(r"```json\n([\s\S]+?)\n```", input_str)
    if match:
        json_str = match.group(1)  # Extract the JSON string
        return json_str
    else:
        return input_str


class ClickTarget(BaseModel):
    """A target which the mouse could be moved to and clicked"""

    description: str = Field(
        description="A long detailed description of the target e.g. A round blue button with the text 'login'"
    )
    purpose: str = Field(
        description="A general purpose of the target e.g. 'log the user in' or 'search for a product'"
    )
    expectation: str = Field(
        description="An expectation on what will happen when you click this target e.g. 'A login screen will appear'"
    )
    near: str = Field(
        description="Describe what is near the target e.g. the 'Get' button is near the text 'Awesome App'"
    )


def crop_box_around(
    image: Image.Image, x: int, y: int, padding: int = 50
) -> Image.Image:
    # Calculate the boundaries of the box
    left = x - padding
    top = y - padding
    right = x + padding
    bottom = y + padding

    # Crop the image
    cropped_img = image.crop((left, top, right, bottom))

    return cropped_img


def image_to_b64(img: Image.Image, image_format="PNG") -> str:
    """Converts a PIL Image to a base64-encoded string with MIME type included.

    Args:
        img (Image.Image): The PIL Image object to convert.
        image_format (str): The format to use when saving the image (e.g., 'PNG', 'JPEG').

    Returns:
        str: A base64-encoded string of the image with MIME type.
    """
    buffer = BytesIO()
    img.save(buffer, format=image_format)
    image_data = buffer.getvalue()
    buffer.close()

    mime_type = f"image/{image_format.lower()}"
    base64_encoded_data = base64.b64encode(image_data).decode("utf-8")
    return f"data:{mime_type};base64,{base64_encoded_data}"


def b64_to_image(base64_str: str) -> Image.Image:
    """Converts a base64 string to a PIL Image object.

    Args:
        base64_str (str): The base64 string, potentially with MIME type as part of a data URI.

    Returns:
        Image.Image: The converted PIL Image object.
    """
    # Strip the MIME type prefix if present
    if "," in base64_str:
        base64_str = base64_str.split(",")[1]

    image_data = base64.b64decode(base64_str)
    image = Image.open(BytesIO(image_data))
    return image


class MouseCoordsPrediction(BaseModel):
    x: int = Field(description="The current X coordinate")
    y: int = Field(description="The current Y coordinate")


def predict_current_coords(
    desktop: Desktop,
    run_id: str,
):
    b64_img = desktop.take_screenshot()
    img = b64_to_image(b64_img)
    size = img.size
    coords = desktop.mouse_coordinates()

    action_id = str(uuid.uuid4())
    img_path = f"runs/{run_id}/online_img/{action_id}.png"
    img.save(img_path)
    rel_path = f"online_img/{action_id}.png"

    coords_prompt = f"Return the mouse coordinates for the GUI image of size [{size[0]}, {size[1]}] in the form [x, y]"

    return {
        "id": str(uuid.uuid4()),
        "image": [rel_path],
        "conversations": [
            {
                "from": "human",
                "value": coords_prompt,
            },
            {"from": "bot", "value": f"[{coords[0]}, {coords[1]}]"},
        ],
    }


class ExpectationValidation(BaseModel):
    valid: bool = Field(
        description="Whether to expectation is validated by the current environment"
    )

class PredictedURL(BaseModel):
    url: str = Field(description="The URL the browser is currently navigated to")


def recognize_url(
    desktop: Desktop,
    router: Router,
    run_id: str,
):
    b64_img = desktop.take_screenshot()
    img = b64_to_image(b64_img)
    coords = desktop.mouse_coordinates()

    action_id = str(uuid.uuid4())
    img_path = f"runs/{run_id}/online_img/{action_id}.png"
    img.save(img_path)
    rel_path = f"online_img/{action_id}.png"

    url_prompt = f"I've provided you with an image of an ubuntu desktop GUI with a chromium browser open. What URL is the browser currently navigated to?"

    thread = RoleThread()
    thread.post(
        role="user",
        msg=f"""I've provided you with an image of an ubuntu desktop GUI with a chromium browser open. What URL is the browser currently navigated to? Please return just the raw JSON object conforming to the schema {PredictedURL.model_json_schema()}. For example if you see the browser is navigated to the URL 'https://www.airbnb.com/host/homes' then you would return {{"url": 'https://www.airbnb.com/host/homes'}}""",
        images=[img],
    )

    resp = router.chat(thread, expect=PredictedURL)

    if not resp.parsed:
        raise ValueError("no parsed response")

    return resp.parsed.url, {
        "id": str(uuid.uuid4()),
        "image": [rel_path],
        "conversations": [
            {
                "from": "human",
                "value": url_prompt,
            },
            {
                "from": "bot",
                "value": resp.parsed.url,
            },
        ],
    }


class ClickTargets(BaseModel):
    targets: List[ClickTarget] = Field(description="A list of click targets")


class IsLoading(BaseModel):
    is_loading: bool = Field(description="Is the web page currently loading")


def is_page_loading(
    desktop: Desktop,
    router: Router,
) -> bool:
    thread = RoleThread()

    b64_img = desktop.take_screenshot()
    img = b64_to_image(b64_img)
    coords_new = desktop.mouse_coordinates()

    thread.post(
        role="user",
        msg=f"""I've provided you with an image of a desktop UI. We are trying to test this webpage, please randomly select the next target to click on
Please return a JSON object that conforms to the schema {IsLoading.model_json_schema()}.
Please return just raw json. For example if the page is still loading you would return {{"is_loading": true}}
            """,
        images=[img],
    )

    resp = router.chat(thread, expect=IsLoading)

    if not resp.parsed:
        raise ValueError("no parsed resp")

    return resp.parsed.is_loading


def pick_next_env_delta(
    current_url: str,
    desktop: Desktop,
    router: Router,
    run_id: str,
):
    thread = RoleThread()

    b64_img = desktop.take_screenshot()
    img = b64_to_image(b64_img)
    coords_new = desktop.mouse_coordinates()

    action_id = str(uuid.uuid4())
    img_path = f"runs/{run_id}/online_img/{action_id}.png"
    img.save(img_path)
    rel_path = f"online_img/{action_id}.png"

    prompt = f"""I've provided you with an image of a desktop UI. We are trying to test this webpage, please randomly select a way you can change the environment through clicking.
For example if you want to open the user settings simply return "open user settings", if you want to highlight the search bar so you can type in it simply return "highlight search bar".
"""

    thread.post(
        role="user",
        msg=prompt,
        images=[img],
    )

    resp = router.chat(thread)

    example = {
        "id": str(uuid.uuid4()),
        "image": [rel_path],
        "conversations": [
            {
                "from": "human",
                "value": prompt,
            },
            {
                "from": "bot",
                "value": resp.msg.text,
            },
        ],
    }

    return resp.msg.text, example


class MoveMouse(BaseModel):
    reason: str = Field(description="reason for moving the mouse to this location")
    x: int = Field(description="x coordinate")
    y: int = Field(description="y coordinate")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    before=before_log(logger, logging.WARNING),
    after=after_log(logger, logging.ERROR),
)
def predict_env_delta_coords(
    delta: str,
    desktop: Desktop,
    router: Router,
    run_id: str,
):
    thread = RoleThread()

    b64_img = desktop.take_screenshot()
    img = b64_to_image(b64_img)
    coords_new = desktop.mouse_coordinates()

    action_id = str(uuid.uuid4())
    img_path = f"runs/{run_id}/online_img/{action_id}.png"
    img.save(img_path)
    rel_path = f"online_img/{action_id}.png"

    prompt = f"""I've provided you with an image of a desktop UI. We are trying to click the screen in the right location which will cause the following environment change: '{delta}'.
The current mouse coordinates are [{coords_new[0]}, {coords_new[1]}]. Please return a raw JSON object adhearing to the schema {MoveMouse.model_json_schema()}. For example 
if our desired delta is to highlight the search bar so we can type in it we could return {{"reason": "we need to click on the search bar which is in the top left part of the screen", "x": 100, "y": 300}}.
    """

    thread.post(
        role="user",
        msg=prompt,
        images=[img],
    )

    resp = router.chat(thread, expect=MoveMouse)

    print("parsing response: ", resp.msg.text)
    if not resp.parsed:
        raise ValueError("could not parse response")

    if resp.parsed.x == coords_new[0] and resp.parsed.y == coords_new[1]:
        raise ValueError("coords are the same")

    def apply_example(new_delta: str):
        new_prompt = f"""I've provided you with an image of a desktop UI. We are trying to click the screen in the right location which will cause the following environment change: '{new_delta}'.
The current mouse coordinates are [{coords_new[0]}, {coords_new[1]}]. Please return the new coordinates in the form [x, y]. For example if we need to open the user settings and the user button is located at (450, 740) we would return [450, 740].
    """
        example = {
            "id": str(uuid.uuid4()),
            "image": [rel_path],
            "conversations": [
                {
                    "from": "human",
                    "value": new_prompt,
                },
                {
                    "from": "bot",
                    "value": f"[{resp.parsed.x}, {resp.parsed.y}]",  # type: ignore
                },
            ],
        }
        return example

    return [resp.parsed.x, resp.parsed.y], apply_example


def predict_click_delta(
    desktop: Desktop,
    router: Router,
    run_id: str,
):
    b64_img = desktop.take_screenshot()
    img = b64_to_image(b64_img)
    coords = desktop.mouse_coordinates()
    size = img.size

    action_id = str(uuid.uuid4())
    img_path = f"runs/{run_id}/online_img/{action_id}.png"
    img.save(img_path)
    rel_path = f"online_img/{action_id}.png"

    click_prompt = f"I've provided you with an image of an ubuntu desktop GUI with the size [{size[0]}, {size[1]}]. In detail, predict the state of the screen after you click the mouse at its current coordinates [{coords[0]}, {coords[1]}]"

    print("clicking")
    desktop.click()

    thread = RoleThread()

    print("sleeping for 5 second")
    time.sleep(5)

    b64_img_new = desktop.take_screenshot()
    img_new = b64_to_image(b64_img_new)

    action_id_new = str(uuid.uuid4())
    img_path_new = f"runs/{run_id}/online_img/{action_id_new}.png"
    img_new.save(img_path_new)
    rel_path_new = f"online_img/{action_id_new}.png"

    change_prompt = f"""I've provided you with two images of a desktop GUI, first is an image of the state of the GUI before the mouse was clicked. 
The second image is an image of the state of the GUI after the mouse was clicked. Please describe the current state of the screen in detail, paying attention to any changes in the screen that may have occured from the click. 
This will be used to train a world model, so please return the response in a form that only describes the changes in the screen e.g. 'A login screen where the user can input their credentials or use social login' 
or if there is no difference in the images then simple return 'no change'."""
    
    change_prompt_compose = f"""Image1: <ImageHere>; Image2: <ImageHere>. I've provided you with two images of a desktop GUI, Image1 is of the state of the GUI before the mouse was clicked. 
Image2 is an image of the state of the GUI after the mouse was clicked. Please describe the current state of the screen in detail, paying attention to any changes in the screen that may have occured from the click. 
This will be used to train a world model, so please return the response in a form that only describes the changes in the screen e.g. 'A login screen where the user can input their credentials or use social login' 
or if there is no difference in the images then simple return 'no change'."""

    thread.post(
        role="user",
        msg=change_prompt,
        images=[img, img_new],
    )

    resp = router.chat(thread)
    print("click delta response: ", resp.msg.text)

    if "no change" in resp.msg.text.lower().strip():
        print("\n!> there was no change to the environment")
        return None, []

    print("\n!> there was a change to the environment")

    return resp.msg.text, [
        {
            "id": str(uuid.uuid4()),
            "image": [rel_path],
            "conversations": [
                {
                    "from": "human",
                    "value": click_prompt,
                },
                {
                    "from": "bot",
                    "value": resp.msg.text,
                },
            ],
        },
        {
            "id": str(uuid.uuid4()),
            "image": [rel_path, rel_path_new],
            "conversations": [
                {
                    "from": "human",
                    "value": change_prompt_compose,
                },
                {
                    "from": "bot",
                    "value": resp.msg.text,
                },
            ],
        },
    ]


def gather_data(
    base_url: str,
    match_url: str,
    desktop: Desktop,
    router: Router,
    run_id: str,
) -> List[dict]:
    data = []

    # choose a direction to move
    print("\n--- choosing the next environment delta...")
    next_delta, example = pick_next_env_delta(base_url, desktop, router, run_id)
    if not next_delta:
        raise ValueError("No next delta")
    data.append(example)
    print("\nadded example: ", example)
    print("next delta: ", next_delta)

    # predict the mouse coordinates
    print("\n--- predicting the delta mouse coordinates...")
    coords, apply_delta_coords = predict_env_delta_coords(
        next_delta, desktop, router, run_id
    )

    # move the mouse
    print("\n--- moving the mouse...")
    desktop.move_mouse(coords[0], coords[1])
    time.sleep(2)

    # predict the mouse coordinates again
    print("\n--- predicting the current mouse coordinates...")
    example = predict_current_coords(desktop, run_id)
    data.append(example)
    print("\nadded example: ", example)

    # predict the click delta
    print("\n--- predicting the click delta...")
    import traceback

    try:
        ground_delta, examples = predict_click_delta(desktop, router, run_id)
        data.extend(examples)
        print("\nadded examples: ", examples)
    except Exception as e:
        print(e)
        print("\n!> could not predict the click delta, skipping")
        traceback.print_exc()
        raise

    if examples:
        print("\n--- applying the click delta...")
        example = apply_delta_coords(ground_delta)
        data.append(example)
        print("\nadded example: ", example)

        # TODO: describe the old click location

    # predict the current browser URL
    print("\n--- recognizing the URL...")
    current_url, example = recognize_url(desktop, router, run_id)
    data.append(example)
    print("url: ", current_url)
    print("url example: ", example)
    print("\nadded example: ", example)

    # check if we have left the site
    if match_url not in current_url:
        print("\n--- we have left the base url, reopening")
        desktop.open_url(base_url)
        time.sleep(30)

    return data


def generate_random_string(length=6):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def log_model_state(model, stage):
    print(f"Model state at {stage}:")
    for name, param in model.named_parameters():
        if param.requires_grad:
            print(
                f"{name}: {param.data.mean()} {param.grad.mean() if param.grad is not None else 'No grad'}"
            )


def check_nan_inf(tensor, name):
    if torch.isnan(tensor).any() or torch.isinf(tensor).any():
        print(f"NaN or Inf detected in {name}")


def examples_to_markdown(json_data, output_file):
    markdown_content = "# Conversations and Images\n\n"

    for item in json_data:
        print("item: ", item)
        print("type: ", type(item))
        markdown_content += f"## ID: {item['id']}\n\n"
        markdown_content += "### Image\n"
        for image_path in item["image"]:
            markdown_content += f"![{image_path}]({image_path})\n\n"

        markdown_content += "### Conversations\n"
        for convo in item["conversations"]:
            from_person = convo["from"]
            message = convo["value"]
            markdown_content += f'**{from_person.capitalize()}:** "{message}"\n\n'

    with open(output_file, "w") as file:
        file.write(markdown_content)
    print(f"Markdown file '{output_file}' has been created.")


import traceback


def gather_env_data(base_url: str, match_url: str, desktop_name: str):
    print("--- gathering environment data...")
    vm = Desktop.find(name=desktop_name)
    if not vm:
        raise ValueError(f"Desktop {desktop_name} not found")
    desktop = Desktop.from_vm(vm[0])
    router = Router.from_env()

    print(f"opening url {base_url}")
    desktop.open_url(base_url)
    time.sleep(20)

    random_string = generate_random_string()
    run_name = f"ssa-{random_string}"
    print(f"\n---run name: {run_name}\n")

    runs_dir = "runs"
    os.makedirs(f"{runs_dir}/{run_name}/online_img/", exist_ok=True)

    i = 0
    total_examples = 0
    while True:
        i += 1
        print(f"\n>>>\n>>> train loop {i}...\n>>>\n")
        # Gather and process new data
        print("gathering data...")
        b64_img = desktop.take_screenshot()
        current_img = b64_to_image(b64_img)
        current_img.save("current.png")

        print("checking if page is loading...")
        loading = is_page_loading(desktop, router)
        print("loading: ", loading)
        if loading:
            print("page is loading...")
            time.sleep(5)
            continue

        try:
            new_data = gather_data(base_url, match_url, desktop, router, run_name)
            print("\ngot new data: ", new_data)
            total_examples += len(new_data)

            for data in new_data:
                print("\ndata: ", data)

            file_path = f"runs/{run_name}/online_{i}.json"
            with open(file_path, "w") as f:
                json.dump(new_data, f, indent=4)

            examples_to_markdown(new_data, f"runs/{run_name}/online_{i}.md")
            print(f"Data saved to {file_path}")
            print("total examples: ", total_examples)

        except Exception as e:
            print("\n---- failue collecting data: ", e)
            traceback.print_exc()
            print("trying the loop again...")
            continue


if __name__ == "__main__":
    import argparse
    from urllib.parse import urlparse

    def get_main_domain(url):
        parsed_url = urlparse(url)
        domain_parts = parsed_url.netloc.split(".")
        return domain_parts[0]

    parser = argparse.ArgumentParser(description="SSA flags")

    # Add a flag (boolean argument)
    parser.add_argument("-u", "--url", type=str, required=True, help="url to learn")
    parser.add_argument("-d", "--desktop", type=str, required=True, help="desktop to use")

    args = parser.parse_args()

    if not args.url:
        print("please provide a url to learn with the --url flag")
        exit(1)

    gather_env_data(args.url, get_main_domain(args.url), args.desktop)
