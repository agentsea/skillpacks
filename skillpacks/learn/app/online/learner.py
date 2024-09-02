from transformers import AutoModelForCausalLM, AutoProcessor
import torch
from torch.optim import AdamW

device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

model = AutoModelForCausalLM.from_pretrained(
    "microsoft/Florence-2-base-ft",
    trust_remote_code=True,
    revision='refs/pr/6'
).to(device)
processor = AutoProcessor.from_pretrained("microsoft/Florence-2-base-ft", 
    trust_remote_code=True, revision='refs/pr/6')

# Freeze the vision encoder
# for param in model.vision_tower.parameters():
#     param.requires_grad = False

optimizer = AdamW(model.parameters(), lr=1e-6)


def process_example(question, answer, image):
    model.train()
    
    # Prepare input
    inputs = processor(text=[question], images=[image], return_tensors="pt", padding=True).to(device)
    labels = processor.tokenizer(text=[answer], return_tensors="pt", padding=True, return_token_type_ids=False).input_ids.to(device)
    
    # Forward pass
    outputs = model(input_ids=inputs["input_ids"], pixel_values=inputs["pixel_values"], labels=labels)
    loss = outputs.loss
    
    # Backward pass and optimization
    loss.backward()
    optimizer.step()
    optimizer.zero_grad()
    
    return loss.item()


def online_fine_tune(data_stream):
    total_loss = 0
    num_examples = 0
    
    for question, answer, image in data_stream:
        loss = process_example(question, answer, image)
        total_loss += loss
        num_examples += 1
        
        if num_examples % 10 == 0:  # Print average loss every 10 examples
            print(f"Average loss after {num_examples} examples: {total_loss / num_examples}")
        
        if num_examples % 100 == 0:  # Save model checkpoint every 100 examples
            model.save_pretrained(f"checkpoint_{num_examples}")
            processor.save_pretrained(f"checkpoint_{num_examples}")
    
    print(f"Final average loss: {total_loss / num_examples}")


    # This is just an example. Replace with your actual data streaming mechanism
def your_data_stream():
    while True:
        # Fetch next example (question, answer, image) from your data source
        yield question, answer, image

online_fine_tune(your_data_stream())