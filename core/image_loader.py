from pathlib import Path

class ImageLoader:
    def __init__(self, target_path: Path, recursive: bool = False):
        self.target_path = target_path
        self.recursive = recursive
        self.extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'}
        
    def load_images(self):
        if self.target_path.is_file():
            if self.target_path.suffix.lower() in self.extensions:
                return [self.target_path]
            return []
            
        images = []
        if self.recursive:
            for p in self.target_path.rglob('*'):
                if p.is_file() and p.suffix.lower() in self.extensions:
                    images.append(p)
        else:
            for p in self.target_path.glob('*'):
                if p.is_file() and p.suffix.lower() in self.extensions:
                    images.append(p)
                    
        return sorted(images)
