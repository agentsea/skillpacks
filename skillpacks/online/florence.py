import os
from unittest.mock import patch
from typing import Optional

import requests
from PIL import Image
from transformers import AutoModelForCausalLM, AutoProcessor
from transformers.dynamic_module_utils import get_imports
from transformers import AutoModelForCausalLM, AutoProcessor
import torch
from torch.optim import AdamW
import wandb

from .base import OnlineCompletionModel


def fixed_get_imports(filename: str | os.PathLike) -> list[str]:
    """Work around for https://huggingface.co/microsoft/phi-1_5/discussions/72."""
    if not str(filename).endswith("/modeling_florence2.py"):
        return get_imports(filename)
    imports = get_imports(filename)
    imports.remove("flash_attn")
    return imports


class Florence2(OnlineCompletionModel):
    """Florence2 online learning model"""

    def __init__(self, lr: float = 1e-6, wandb_project: Optional[str] = None, gradient_acc: int = 4) -> None:
        with patch("transformers.dynamic_module_utils.get_imports", fixed_get_imports):

            if torch.cuda.is_available():
                self.device = torch.device("cuda")
            elif torch.backends.mps.is_available():
                self.device = torch.device("mps")
            else:
                self.device = torch.device("cpu")

            print("using device: ", self.device)

            model_name = "microsoft/Florence-2-large-ft"

            self.model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True).to(self.device)
            self.processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)

            self.optimizer = AdamW(self.model.parameters(), lr=lr)
            self.total_loss = 0.0
            self.num_examples = 0

        self.gradient_accumulation_steps = gradient_acc
        self.optimizer.zero_grad() 

        self.use_wandb = False
        if wandb_project:
            wandb.init(project=wandb_project)
            wandb.watch(self.model)
            wandb.config.update({
                "learning_rate": lr,
                "device": str(self.device),
                "model": model_name
            })
            self.use_wandb = True

    def check_trainable_parameters(self):
        for name, param in self.model.named_parameters():
            if not param.requires_grad:
                print(f"Parameter {name} is not trainable")

    def learn(self, prompt: str, image: str | Image.Image, response: str) -> float:
        if isinstance(image, str):
            image = Image.open(requests.get(image, stream=True).raw)
        
        self.model.train()

        self.check_trainable_parameters()
        
        # Prepare input
        inputs = self.processor(text=[prompt], images=[image], return_tensors="pt", padding=True).to(self.device)
        labels = self.processor.tokenizer(text=[response], return_tensors="pt", padding=True, return_token_type_ids=False).input_ids.to(self.device)
        
        # Forward pass
        outputs = self.model(input_ids=inputs["input_ids"], pixel_values=inputs["pixel_values"], labels=labels)
        loss = outputs.loss
        
        # Normalize the loss to account for gradient accumulation
        loss = loss / self.gradient_accumulation_steps
        
        # Backward pass
        loss.backward()
        
        self.total_loss += loss.item()

        if self.use_wandb:
            wandb.log({"loss": loss.item()})

        self.num_examples += 1

        # Only update weights and zero gradients after accumulating enough steps
        if self.num_examples % self.gradient_accumulation_steps == 0:
            self.optimizer.step()
            self.optimizer.zero_grad()

        return loss.item() * self.gradient_accumulation_steps  # Return the non-normalized loss for logging

    def complete(self, prompt: str, image: str | Image.Image) -> str:
        if isinstance(image, str):
            image = Image.open(requests.get(image, stream=True).raw)

        inputs = self.processor(text=prompt, images=image, return_tensors="pt").to(self.device)
        
        # Move inputs to the same device as the model
        # inputs = {k: v.to(self.device) for k, v in inputs.items()}

        generated_ids = self.model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=1024,
            num_beams=3,
        )
        
        # Move generated_ids back to CPU for decoding
        generated_ids = generated_ids.cpu()
        
        generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        parsed_answer = self.processor.post_process_generation(generated_text, task=prompt, image_size=(image.width, image.height))
        return parsed_answer
    
    def save(self, path: str = "./output") -> None:
        os.makedirs(path, exist_ok=True)

        self.model.save_pretrained(os.path.join(path, f"checkpoint_{self.num_examples}"))
        self.processor.save_pretrained(os.path.join(path, f"checkpoint_{self.num_examples}"))

    def finish(self) -> None:
        if self.use_wandb:
            wandb.finish()
