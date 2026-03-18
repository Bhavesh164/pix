from PIL import Image
import os

os.makedirs('test_photos', exist_ok=True)
for i in range(1000):
    img = Image.new('RGB', (160, 160), color=(i%255, (i*5)%255, (i*13)%255))
    img.save(f'test_photos/photo_{i:03d}.jpg')
    
print("Created 1000 test photos in test_photos/")
