import base64
from io import BytesIO
import json
import random

from agentdesk import Desktop
from PIL import Image

from skillpacks.online import Florence2


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


desk = Desktop.ec2()

florence = Florence2(lr=1e-5, wandb_project="llm-online")

i = 0
while True:
    i += 1

    screen_b64 = desk.take_screenshot()
    screen = b64_to_image(screen_b64)

    screen.save("latest_screen.png")

    prompt = "Predict the mouse cursor coordinates"

    coords = desk.mouse_coordinates()
    loss = florence.learn(prompt=prompt, image=screen, response=json.dumps(coords))

    with open("training_data.jsonl", "a") as f:
        data = {
            "prompt": prompt,
            "image": screen_b64,  # Save the base64 encoded image
            "response": coords
        }
        json.dump(data, f)
        f.write("\n") 

    if i % 100 == 0:
        print("Train loop: ", i, " loss: ", loss)

    
    x = random.randint(0, screen_size["x"])
    y = random.randint(0, screen_size["y"])

    desk.move_mouse(x=x, y=y)