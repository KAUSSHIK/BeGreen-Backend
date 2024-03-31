# this file is for training the OPEN AI MODEL
import os
import openai
import json


# Set the OpenAI API Key
openai.api_key = os.getenv('OPENAI_API_KEY')


# Load activities from a JSON file
with open('activities.json', 'r') as f:
    activities_data = json.load(f)

# Convert Activities to a dictionary
ACTIVITIES = activities_data['activities']

# Initialize Dataset
dataset = []

for activity, points in ACTIVITIES.items():
    prompt = f"How many sustainability points do I get for {activity}?"
    example = f"{prompt}\t{points}"
    dataset.append(example)

# Fine Tune the Model
response = openai.FineTune.create_training(
    model="text-davinci-002",                 # Model to fine-tune
    data=dataset,                             # Training data
    name="sustainability_points_predictor"    # Name for the fine-tuned model
)

# Retrieve the fine-tuned model
fine_tuned_model_id = response['model']

# Save the fine-tuned model ID to a text file
with open("fine_tuned_model_id.txt", "w") as file:
    file.write(fine_tuned_model_id)