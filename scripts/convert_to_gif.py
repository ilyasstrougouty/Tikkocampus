import subprocess
import os

input_mp4 = r"c:\Users\trily\Desktop\Learning\TIKTOK RAG\assets\demo.mp4"
output_gif = r"c:\Users\trily\Desktop\Learning\TIKTOK RAG\assets\demo.gif"

# Optimize filters for a smaller GIF:
# - Width: 600px (decreased from 800px)
# - FPS: 8 (decreased from 12)
# - Dithering: sierra2_4a (helps reduce size)
filters = "fps=8,scale=600:-1:flags=lanczos"

print(f"Converting {input_mp4} to {output_gif} with optimized settings...")

# Palette generation
palette = "temp_palette.png"
subprocess.run(["ffmpeg", "-y", "-i", input_mp4, "-vf", f"{filters},palettegen", palette], check=True)

# GIF generation with dithering optimization
subprocess.run(["ffmpeg", "-y", "-i", input_mp4, "-i", palette, "-lavfi", f"{filters} [x]; [x][1:v] paletteuse=dither=sierra2_4a", output_gif], check=True)

# Clean up
if os.path.exists(palette):
    os.remove(palette)

print("Optimization complete!")
