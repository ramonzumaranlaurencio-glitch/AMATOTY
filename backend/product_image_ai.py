# Librerías para IA de reconocimiento de imágenes y explicación automática
import torch
import torchvision.transforms as transforms
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
import requests
import io

# Cargar modelo BLIP (puedes cambiar por otro más avanzado si lo deseas)
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

def describe_image_from_url(image_url):
    response = requests.get(image_url)
    img = Image.open(io.BytesIO(response.content)).convert('RGB')
    return describe_image(img)

def describe_image(img):
    inputs = processor(img, return_tensors="pt")
    out = model.generate(**inputs)
    caption = processor.decode(out[0], skip_special_tokens=True)
    return caption

# Ejemplo de uso:
if __name__ == "__main__":
    url = "https://example.com/product-image.jpg"
    print("Descripción IA:", describe_image_from_url(url))
