from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

import boto3
from PIL import Image, ImageDraw, ImageFont


DEJAVU_BOLD_PATH = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")


class BotObjectStorage:
    def __init__(
        self,
        *,
        access_key: str | None,
        secret_key: str | None,
        bucket_name: str | None,
        endpoint_url: str,
        region_name: str,
    ) -> None:
        self.bucket_name = bucket_name
        self._client = None
        if access_key and secret_key and bucket_name:
            self._client = boto3.client(
                "s3",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                endpoint_url=endpoint_url,
                region_name=region_name,
            )

    @property
    def enabled(self) -> bool:
        return self._client is not None and self.bucket_name is not None

    def upload_bytes(self, key: str, payload: bytes, content_type: str) -> str:
        if not self.enabled or self._client is None or self.bucket_name is None:
            raise RuntimeError("S3 is not configured")
        self._client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=payload,
            ContentType=content_type,
        )
        return key


def create_postcard(photo_bytes: bytes, footer_date: str) -> bytes:
    canvas_width = 1080
    canvas_height = 1350
    footer_height = int(canvas_height * 0.2)
    photo_height = canvas_height - footer_height

    source = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
    scale = max(canvas_width / source.width, photo_height / source.height)
    resized = source.resize((int(source.width * scale), int(source.height * scale)))
    left = (resized.width - canvas_width) // 2
    top = (resized.height - photo_height) // 2
    cropped = resized.crop((left, top, left + canvas_width, top + photo_height))

    card = Image.new("RGB", (canvas_width, canvas_height), color="#fcf7fb")
    card.paste(cropped, (0, 0))

    draw = ImageDraw.Draw(card)
    draw.rectangle((0, photo_height, canvas_width, canvas_height), fill="#f3e6f7")
    draw.line((80, photo_height, canvas_width - 80, photo_height), fill="#d4b3df", width=6)

    try:
        title_font = ImageFont.truetype(str(DEJAVU_BOLD_PATH), 46)
        date_font = ImageFont.truetype(str(DEJAVU_BOLD_PATH), 86)
    except OSError:
        title_font = ImageFont.load_default()
        date_font = ImageFont.load_default()

    text_bbox = draw.textbbox((0, 0), footer_date, font=date_font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    accent_text = "Ваше свидание"
    accent_bbox = draw.textbbox((0, 0), accent_text, font=title_font)
    accent_width = accent_bbox[2] - accent_bbox[0]
    accent_height = accent_bbox[3] - accent_bbox[1]
    accent_y = photo_height + 36
    draw.text(
        ((canvas_width - accent_width) / 2, accent_y),
        accent_text,
        fill="#7b5ba2",
        font=title_font,
    )
    draw.text(
        ((canvas_width - text_width) / 2, accent_y + accent_height + 18),
        footer_date,
        fill="#5b3f7d",
        font=date_font,
    )

    output = io.BytesIO()
    card.save(output, format="JPEG", quality=92)
    return output.getvalue()


def build_memory_keys(room_id: str, user_id: int) -> tuple[str, str]:
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    base = f"date-memories/{room_id}"
    return (
        f"{base}/user-{user_id}-photo-{stamp}.jpg",
        f"{base}/user-{user_id}-postcard-{stamp}.jpg",
    )
