# this file is for training the OPEN AI MODEL
import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client with the API Key
client = OpenAI(api_key=os.getenv('OPEN_AI_API_KEY'))

# Get the absolute path to the dataset.txt file
dataset_file_path = os.path.abspath('dataset.txt')

training_file = client.files.create(
    file=open("dataset.jsonl", "rb"), purpose="fine-tune"
)


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

# # Write the dataset to a file
# with open('dataset.txt', 'w') as f:
#     for item in dataset:
#         data = {
#             "prompt": item.split('\t')[0],
#             "completion": "You get" + item.split('\t')[1] + " sustainability points."
#         }
#         f.write(json.dumps(data) + "\n")
    
with open('dataset.jsonl', 'w') as f:
    for example in dataset:
        json.dump({"prompt": example.split('\t')[0], "completion": "You get " + example.split('\t')[1] + " sustainability points."}, f)
        f.write('\n')  # Newline between each JSON object

  
response = client.fine_tuning.jobs.create(
    training_file=training_file.id,  # Pass the JSONL file
    model="davinci-002",
    suffix="sust-points"
)

print(response)
# # Retrieve the fine-tuned model ID
# fine_tuned_model_id = response

# # Save the fine-tuned model ID to a text file
# with open("fine_tuned_model_id.txt", "w") as file:
#     file.write(fine_tuned_model_id)