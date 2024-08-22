import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np
from typing import Tuple

# Load pre-trained model and tokenizer
model = "cardiffnlp/twitter-roberta-base-sentiment"
tokenizer = AutoTokenizer.from_pretrained(model)
model = AutoModelForSequenceClassification.from_pretrained(model)

def analyze_sentiment(text: str) -> Tuple[int, np.ndarray]:
    """
    Analyzes the sentiment of the given text using a pre-trained RoBERTa model.

    Args:
        text (str): The input text to analyze.

    Returns:
        Tuple[int, np.ndarray]: The predicted sentiment class (0: negative, 1: neutral, 2: positive) 
                                and the associated probabilities for each class.
    """
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length = 512)
    input_ids, attention_mask = inputs["input_ids"], inputs["attention_mask"]

    outputs = model(input_ids=input_ids, attention_mask=attention_mask)
    logits = outputs.logits

    probabilities = torch.nn.functional.softmax(logits, dim = -1)
    predicted_class = torch.argmax(probabilities, dim = -1).item()


    return predicted_class, probabilities.detach().numpy()