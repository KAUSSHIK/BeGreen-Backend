# this file is for training the OPEN AI MODEL
import os
import openai


#Set the OpenAI API Key
openai.api_key = os.getenv('OPENAI_API_KEY')

#Load Dataset
dataset = []

fine_tuned_model = None

# Fine Tune the Model

response = openai.FineTune.create(
    model = "text-davinci-002",                 # Model to fine-tune
    training_file = dataset,                    # Training data
    suffix = "sustainability_points_predictor", # Suffix to add to the model name
)

# Retrieve the fine-tuned model
fine_tuned_model_id = response.fine_tuned_model

# Save the fine-tuned model as a variable in a text file
with open ("fine_tuned_model_id.txt", "w") as file:
    file.write(fine_tuned_model_id)

