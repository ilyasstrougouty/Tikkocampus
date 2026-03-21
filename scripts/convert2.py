import subprocess
input_img = r"C:\Users\trily\.gemini\antigravity\brain\dddb2833-03ea-4aa3-b1b4-516a2d0c0e2c\uploaded_media_1773853521654.img"
output_ico = r"C:\Users\trily\Desktop\Learning\TIKTOK RAG\electron-app\app_logo.ico"

try:
    from PIL import Image
    img = Image.open(input_img).convert("RGBA")
    img.save(output_ico, format="ICO", sizes=[(256, 256)])
    print("Successfully generated app_logo.ico")
except Exception as e:
    print(f"Error: {e}")
