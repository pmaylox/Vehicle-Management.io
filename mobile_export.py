import base64
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps


def build_mobile_backup(vehicles):
    records = []

    for vehicle in vehicles:
        record = vehicle.to_dict()

        if vehicle.photo_path:
            path = Path(vehicle.photo_path)

            if not path.is_absolute():
                path = Path(__file__).resolve().parent / path

            try:
                with Image.open(path) as source:
                    photo = ImageOps.exif_transpose(source).convert("RGBA")
                    photo.thumbnail(
                        (900, 900),
                        Image.Resampling.LANCZOS
                    )

                buffer = BytesIO()
                photo.save(buffer, format="PNG", optimize=True)

                encoded = base64.b64encode(
                    buffer.getvalue()
                ).decode("ascii")

                image_data = f"data:image/png;base64,{encoded}"

                if len(image_data) > 1_400_000:
                    raise ValueError(
                        "Photo is too large. Choose a smaller image."
                    )

                record["mobile_photo"] = image_data

            except (
                OSError,
                ValueError,
                Image.DecompressionBombError
            ) as error:
                raise ValueError(
                    f"Could not export the photo for "
                    f"{vehicle.name}: {error}"
                ) from error

        records.append(record)

    return {
        "vehicles": records,
        "current": 0
    }