import os
import requests
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Downloads placeholder images for categories'

    def handle(self, *args, **options):
        # Create media/categories directory if it doesn't exist
        categories_dir = os.path.join(settings.MEDIA_ROOT, 'categories')
        os.makedirs(categories_dir, exist_ok=True)

        # Image URLs for each category
        category_images = {
            'vegetables.jpg': 'https://source.unsplash.com/800x600/?vegetables',
            'fruits.jpg': 'https://source.unsplash.com/800x600/?fruits',
            'grains.jpg': 'https://source.unsplash.com/800x600/?grains',
            'dairy.jpg': 'https://source.unsplash.com/800x600/?dairy',
            'herbs-spices.jpg': 'https://source.unsplash.com/800x600/?spices'
        }

        for filename, url in category_images.items():
            filepath = os.path.join(categories_dir, filename)
            if not os.path.exists(filepath):
                try:
                    response = requests.get(url)
                    response.raise_for_status()
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    self.stdout.write(self.style.SUCCESS(f'Successfully downloaded {filename}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Failed to download {filename}: {str(e)}'))
            else:
                self.stdout.write(self.style.WARNING(f'{filename} already exists, skipping'))
