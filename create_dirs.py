import os

# Create necessary directories
dirs = ['templates', 'static', 'static/css', 'static/js']
for dir_name in dirs:
    os.makedirs(dir_name, exist_ok=True)
print("Directories created successfully!")
