
import uuid						# unique filenames
from io import BytesIO			# working with image bytes in memory
from pathlib import Path		# path operations

from PIL import Image, ImageOps	# image processing

PROFILE_PICS_DIR = Path("media/profile_pics")	# directory for profile pics, mounted in main.py

# image processing with Pillow is CPU-bound and sync - fastapi is async, so we need to run the image processing in a threadpool to avoid blocking the event loop
def process_profile_image(content: bytes) -> str:
	with Image.open(BytesIO(content)) as original:		# this will raise exceptions if the image is invalid or corrupted which will be caught in the route handler
		img = ImageOps.exif_transpose(original)			# if the image has EXIF orientation data, this will rotate/flip the image to the correct orientation

		img = ImageOps.fit(img, (300, 300), method=Image.Resampling.LANCZOS)	# fit to 300x300 pixels, cropping if necessary, using high-quality resampling

		if img.mode in ("RGBA", "LA", "P"):
			img = img.convert("RGB")				# convert to RGB if the image has an alpha channel or is in a palette mode, since JPEG does not support alpha channels

		filename = f"{uuid.uuid4().hex}.jpg"		# generate a unique filename for the processed image using a UUID and save it as a JPEG file
		filepath = PROFILE_PICS_DIR / filename

		PROFILE_PICS_DIR.mkdir(parents=True, exist_ok=True)		# make sure directory exists, create it if it doesn't

		img.save(filepath, "JPEG", quality=85, optimize=True)	# save file as JPEG with quality 85 and optimize for size

	return filename


## Delete Profile Image Function
def delete_profile_image(filename: str | None) -> None:
	if filename is None:
		return

	filepath = PROFILE_PICS_DIR / filename
	if filepath.exists():
		filepath.unlink()	# delete the file if it exists, otherwise do nothing

