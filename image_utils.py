
import uuid						# unique filenames
from io import BytesIO			# working with image bytes in memory
#from pathlib import Path		# path operations

from PIL import Image, ImageOps	# image processing

import boto3 	# AWS management
from starlette.concurrency import run_in_threadpool
from config import settings

#PROFILE_PICS_DIR = Path("media/profile_pics")	# directory for profile pics, mounted in main.py

# _get_s3_client helper for image_utils.py
#  leading _ is Python convention for private internal function - shouldn't be imported into other files
def _get_s3_client ():
	return boto3.client(
		"s3",
		region_name=settings.s3_region,
		aws_access_key_id=(
			settings.s3_access_key_id.get_secret_value()
			if settings.s3_access_key_id
			else None
		),
		aws_secret_access_key=(
			settings.s3_secret_access_key.get_secret_value()
			if settings.s3_secret_access_key
			else None
		),
		endpoint_url=settings.s3_endpoint_url,
	)


# image processing with Pillow is CPU-bound and sync - fastapi is async, so we need to run the image processing in a threadpool to avoid blocking the event loop
#def process_profile_image (content: bytes) -> str:
def process_profile_image (content: bytes) -> tuple[bytes, str]:
	with Image.open(BytesIO(content)) as original:		# this will raise exceptions if the image is invalid or corrupted which will be caught in the route handler
		img = ImageOps.exif_transpose(original)			# if the image has EXIF orientation data, this will rotate/flip the image to the correct orientation

		img = ImageOps.fit(img, (300, 300), method=Image.Resampling.LANCZOS)	# fit to 300x300 pixels, cropping if necessary, using high-quality resampling

		if img.mode in ("RGBA", "LA", "P"):
			img = img.convert("RGB")				# convert to RGB if the image has an alpha channel or is in a palette mode, since JPEG does not support alpha channels

		filename = f"{uuid.uuid4().hex}.jpg"		# generate a unique filename for the processed image using a UUID and save it as a JPEG file

		#filepath = PROFILE_PICS_DIR / filename
		#
		#PROFILE_PICS_DIR.mkdir(parents=True, exist_ok=True)		# make sure directory exists, create it if it doesn't
		#
		#img.save(filepath, "JPEG", quality=85, optimize=True)	# save file as JPEG with quality 85 and optimize for size

		# store file in a BytesIO object for upload to AWS S3 bucket storage
		output = BytesIO()
		img.save(output, "JPEG", quality=85, optimize=True)
		output.seek(0)	# rewind to beginning

	#return filename
	return output.read(), filename


## Delete Profile Image Function
#def delete_profile_image (filename: str | None) -> None:
#	if filename is None:
#		return
#
#	filepath = PROFILE_PICS_DIR / filename
#	if filepath.exists():
#		filepath.unlink()	# delete the file if it exists, otherwise do nothing

## _upload_to_s3 and _delete_from_s3 for image_utils.py
# key is the filepath to store it as on S3
# these are sync and blocking - they will stop the event loop until done - need to run in thread pool
def _upload_to_s3 (file_bytes: bytes, key: str) -> None:
	s3 = _get_s3_client()
	s3.upload_fileobj(
		BytesIO(file_bytes),
		settings.s3_bucket_name,
		key,
		ExtraArgs={"ContentType": "image/jpeg"},
	)

def _delete_from_s3 (key: str) -> None:
	s3 = _get_s3_client()
	s3.delete_object(Bucket=settings.s3_bucket_name, Key=key)

## Async S3 wrappers for image_utils.py
async def upload_profile_image (file_bytes: bytes, filename: str) -> None:
	key = f"profile_pics/{filename}"
	await run_in_threadpool(_upload_to_s3, file_bytes, key)

async def delete_profile_image (filename: str | None) -> None:
	if filename is None:
		return
	key = f"profile_pics/{filename}"
	await run_in_threadpool(_delete_from_s3, key)



