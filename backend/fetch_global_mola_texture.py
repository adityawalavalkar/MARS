"""Build the intro globe texture from verified NASA Trek MOLA WMTS tiles.

The requested matrix is selected from GetCapabilities by output dimensions;
tile identifiers, style, matrix set, and image extension all come from that
document. Tiles are mosaicked in the service's equirectangular row/column order.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET

import requests
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = REPO_ROOT / "frontend" / "public" / "textures" / "mars.jpg"
CAPABILITIES = (
    "https://trek.nasa.gov/tiles/Mars/EQ/"
    "Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/WMTSCapabilities.xml"
)
NS = {"w": "http://www.opengis.net/wmts/1.0", "o": "http://www.opengis.net/ows/1.1"}


def main() -> None:
    response = requests.get(CAPABILITIES, timeout=30)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    layer = next(
        item for item in root.findall(".//w:Layer", NS)
        if item.findtext("o:Identifier", namespaces=NS) == "Mars_MGS_MOLA_ClrShade_merge_global_463m"
    )
    style = layer.findtext("w:Style/o:Identifier", namespaces=NS)
    image_format = layer.findtext("w:Format", namespaces=NS)
    resource = next(item for item in layer.findall("w:ResourceURL", NS) if item.get("resourceType") == "tile")
    template = resource.get("template")
    matrix_set = layer.findtext("w:TileMatrixSetLink/w:TileMatrixSet", namespaces=NS)
    matrices = root.findall(".//w:TileMatrixSet[o:Identifier='" + matrix_set + "']/w:TileMatrix", NS)
    choices = []
    for matrix in matrices:
        ident = matrix.findtext("o:Identifier", namespaces=NS)
        width = int(float(matrix.findtext("w:MatrixWidth", namespaces=NS)))
        height = int(float(matrix.findtext("w:MatrixHeight", namespaces=NS)))
        tile_w = int(matrix.findtext("w:TileWidth", namespaces=NS))
        tile_h = int(matrix.findtext("w:TileHeight", namespaces=NS))
        if width * tile_w >= 4096 and height * tile_h >= 2048:
            choices.append((width * tile_w * height * tile_h, ident, width, height, tile_w, tile_h))
    _, matrix, columns, rows, tile_width, tile_height = min(choices)
    output = Image.new("RGB", (columns * tile_width, rows * tile_height))

    def fetch(row: int, col: int) -> tuple[int, int, Image.Image]:
        url = (template.replace("{Style}", style).replace("{TileMatrixSet}", matrix_set)
               .replace("{TileMatrix}", matrix).replace("{TileRow}", str(row)).replace("{TileCol}", str(col)))
        tile_response = requests.get(url, timeout=40)
        tile_response.raise_for_status()
        return row, col, Image.open(BytesIO(tile_response.content)).convert("RGB")

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(fetch, row, col) for row in range(rows) for col in range(columns)]
        for future in as_completed(futures):
            row, col, tile = future.result()
            output.paste(tile, (col * tile_width, row * tile_height))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    output.save(OUTPUT, format="JPEG", quality=94, optimize=True, progressive=True)
    print(f"Saved {OUTPUT} ({output.width}x{output.height}, {image_format}, matrix {matrix}).")


if __name__ == "__main__":
    main()
