import subprocess
import os

input_mp4 = r"c:\Users\trily\Desktop\Learning\TIKTOK RAG\assets\demo1.mp4"
output_gif = r"c:\Users\trily\Desktop\Learning\TIKTOK RAG\assets\demo.gif"

# High-quality filters for a short <11s video
# - fps: 12
# - scale: 800px width
filters = "fps=12,scale=800:-1:flags=lanczos"

print(f"Converting {input_mp4} to {output_gif} with HIGH QUALITY settings...")

# Palette generation (full 256 colors)
palette = "temp_palette.png"
subprocess.run(["ffmpeg", "-y", "-i", input_mp4, "-vf", f"{filters},palettegen=stats_mode=diff", palette], check=True)

# GIF generation with sierra2_4a dithering (best quality)
subprocess.run(["ffmpeg", "-y", "-i", input_mp4, "-i", palette, "-lavfi", f"{filters} [x]; [x][1:v] paletteuse=dither=sierra2_4a", output_gif], check=True)

# Clean up
if os.path.exists(palette):
    os.remove(palette)
    
size_mb = os.path.getsize(output_gif) / (1024 * 1024)
print(f"High Quality conversion complete! Final GIF size: {size_mb:.2f} MB")
