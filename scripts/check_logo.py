from PIL import Image
import numpy as np

try:
    img = Image.open(r"C:\Users\trily\Desktop\Learning\TIKTOK RAG\web\logo.png").convert("RGBA")
    data = np.array(img)
    alpha = data[:, :, 3]
    
    # Print a tiny ASCII version
    h, w = alpha.shape
    new_h, new_w = 40, 80 # ASCII aspect ratio
    small = Image.fromarray(alpha).resize((new_w, new_h))
    small_data = np.array(small)
    
    print(f"Image size: {w}x{h}")
    for y in range(new_h):
        line = ""
        for x in range(new_w):
            line += "#" if small_data[y, x] > 128 else " "
        print(line)
except Exception as e:
    print(f"Error: {e}")
