#!/usr/bin/env python3
"""Create a test image with a car for CamPark testing"""
from PIL import Image, ImageDraw, ImageFont
import os

# Create a 1920x1080 image (typical camera resolution)
width, height = 1920, 1080
img = Image.new('RGB', (width, height), color='#87CEEB')  # Sky blue background

draw = ImageDraw.Draw(img)

# Draw a simple road (gray rectangle)
draw.rectangle([(0, 700), (width, height)], fill='#555555')

# Draw lane markings (white dashed lines)
for x in range(0, width, 100):
    draw.rectangle([(x, 850), (x + 50, 860)], fill='white')

# Draw a simple car (rectangle with wheels)
car_x, car_y = 800, 750
car_width, car_height = 200, 100

# Car body (blue)
draw.rectangle([(car_x, car_y), (car_x + car_width, car_y + car_height)], fill='#0066CC')

# Car windows (lighter blue)
draw.rectangle([(car_x + 20, car_y + 10), (car_x + 80, car_y + 40)], fill='#66B3FF')
draw.rectangle([(car_x + 120, car_y + 10), (car_x + 180, car_y + 40)], fill='#66B3FF')

# Wheels (black circles)
wheel_radius = 20
draw.ellipse([(car_x + 30 - wheel_radius, car_y + car_height - 10), 
              (car_x + 30 + wheel_radius, car_y + car_height + 30)], fill='black')
draw.ellipse([(car_x + car_width - 30 - wheel_radius, car_y + car_height - 10), 
              (car_x + car_width - 30 + wheel_radius, car_y + car_height + 30)], fill='black')

# Add text
try:
    # Try to use a default font, fallback to default if not available
    font = ImageFont.truetype("arial.ttf", 40)
except:
    font = ImageFont.load_default()

draw.text((50, 50), "CamPark Test Image", fill='white', font=font)
draw.text((50, 100), "Vehicle Detection Test", fill='white', font=font)

# Save the image
output_path = os.path.join(os.path.dirname(__file__), 'test_snapshot.jpg')
img.save(output_path, 'JPEG', quality=95)
print(f"✅ Test image created: {output_path}")
print(f"   Size: {width}x{height}")
print(f"   Contains: 1 car (blue sedan)")
