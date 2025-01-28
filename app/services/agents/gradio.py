import gradio as gr
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import decode_predictions, preprocess_input
import numpy as np
from PIL import Image

# 사전 학습된 모델 로드
model = MobileNetV2(weights="imagenet")

def classify_image(image):
    image = image.resize((224, 224))
    image_array = np.array(image)
    image_array = preprocess_input(image_array[np.newaxis, ...])
    preds = model.predict(image_array)
    return decode_predictions(preds, top=3)[0]

# Gradio 인터페이스 생성
interface = gr.Interface(fn=classify_image, inputs="image", outputs="label")

# 애플리케이션 실행
interface.launch()
