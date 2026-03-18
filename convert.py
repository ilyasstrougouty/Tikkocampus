import subprocess
input_img = r"C:\Users\trily\.gemini\antigravity\brain\dddb2833-03ea-4aa3-b1b4-516a2d0c0e2c\uploaded_media_1773847074239.img"
output_png = r"C:\Users\trily\Desktop\Learning\TIKTOK RAG\electron-app\app_logo.png"
output_ico = r"C:\Users\trily\Desktop\Learning\TIKTOK RAG\electron-app\app_logo.ico"

subprocess.run(["ffmpeg", "-i", input_img, "-y", output_png], check=True)

from PIL import Image
img = Image.open(output_png).convert("RGBA")
img.save(output_ico, format="ICO", sizes=[(256, 256)])
print("Successfully generated app_logo.png and app_logo.ico")
