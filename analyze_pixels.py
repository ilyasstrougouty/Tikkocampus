from PIL import Image
import numpy as np

img = Image.open(r"C:\Users\trily\Desktop\Learning\TIKTOK RAG\web\logo.png").convert("RGB")
data = np.array(img)

# Sample a 10x10 grid to see typical colors
print("Pixel Samples (Top-Left 5x5):")
print(data[:5, :5, :])

# Calculate average brightness to find a threshold
brightness = np.mean(data, axis=2)
print(f"Min brightness: {np.min(brightness)}")
print(f"Max brightness: {np.max(brightness)}")
print(f"Mean brightness: {np.mean(brightness)}")

# Find the most common color (likely background)
pixels = data.reshape(-1, 3)
unique, counts = np.unique(pixels, axis=0, return_counts=True)
most_common = unique[np.argmax(counts)]
print(f"Most common color (background?): {most_common}")
