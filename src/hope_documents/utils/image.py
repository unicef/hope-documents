import base64

from django.core.files.uploadedfile import UploadedFile


def get_image_base64(image_file: UploadedFile) -> str:
    image_file.seek(0)
    image_data = image_file.read()
    base64_data = base64.b64encode(image_data)
    base64_string = base64_data.decode("utf-8")
    image_content_type = image_file.content_type
    return f"data:{image_content_type};base64,{base64_string}"
