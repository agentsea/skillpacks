import json
from PIL import Image
import requests

import torch
import wandb

from .florence import Florence2

class FlorenceCoords(Florence2):

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
        ce_loss = outputs.loss
        
        # Parse the model's output to get predicted coordinates
        generated_text = self.processor.batch_decode(outputs.logits.argmax(dim=-1), skip_special_tokens=True)[0]
        print("generated_text:", generated_text)
        
        # Parse correct coordinates from response
        correct_coords = self.extract_coordinates(response)
        print("correct coords:", correct_coords)
        
        try:
            predicted_coords = self.extract_coordinates(generated_text)
            print("predicted coords:", predicted_coords)
            if predicted_coords and correct_coords:
                distance_loss = self.calculate_coordinate_loss(predicted_coords, correct_coords)
                print("distance loss:", distance_loss)
                combined_loss = ce_loss + distance_loss
            else:
                raise ValueError("Coordinates not found in model output or response")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Error processing coordinates: {e}. Using only cross-entropy loss: {generated_text}")
            distance_loss = torch.tensor(2.0).to(self.device)
            combined_loss = ce_loss + distance_loss

        # Normalize the loss to account for gradient accumulation
        combined_loss = combined_loss / self.gradient_accumulation_steps
        
        # Backward pass
        combined_loss.backward()
        
        self.total_loss += combined_loss.item()

        if self.use_wandb:
            wandb.log({
                "total_loss": combined_loss.item(),
                "ce_loss": ce_loss.item(),
                "distance_loss": distance_loss.item() if isinstance(distance_loss, torch.Tensor) else 0.0
            })

        self.num_examples += 1

        # Only update weights and zero gradients after accumulating enough steps
        if self.num_examples % self.gradient_accumulation_steps == 0:
            self.optimizer.step()
            self.optimizer.zero_grad()

        return combined_loss.item() * self.gradient_accumulation_steps  # Return the non-normalized loss for logging

    def extract_coordinates(self, text: str) -> tuple[float, float]:
        coords = json.loads(text)
        return (coords[0], coords[1])

    def calculate_coordinate_loss(self, predicted_coords: tuple[float, float], correct_coords: tuple[float, float], lambda_coord: float = 1.0) -> torch.Tensor:
        pred_x, pred_y = predicted_coords
        correct_x, correct_y = correct_coords
        
        # Calculate Euclidean distance
        distance = torch.sqrt(torch.tensor((pred_x - correct_x)**2 + (pred_y - correct_y)**2, device=self.device))

        width = 1280 # image width
        height = 1024  # image height
        max_distance = torch.sqrt(torch.tensor(width**2 + height**2, dtype=torch.float32))
        
        normalized_distance = torch.clamp(distance / max_distance, 0, 1)
        
        return normalized_distance * lambda_coord