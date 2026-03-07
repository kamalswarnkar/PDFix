import os
import uuid
import subprocess
from django.conf import settings

def docx_to_pdf(file):
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    input_name = f"{uuid.uuid4()}.docx"
    input_path = os.path.join(settings.MEDIA_ROOT, input_name)

    with open(input_path, "wb+") as f:
        for chunk in file.chunks():
            f.write(chunk)
    
    subprocess.run([
        "soffice",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        settings.MEDIA_ROOT,
        input_path
    ])

    output_name = input_name.replace(".docx", ".pdf")

    return output_name