from typing import Any, Final

PDF_IMAGE_DPI: Final[int] = 200
EXTRACT_IMAGE_BLOCK_TYPES: Final[list[str]] = ["Image", "Table"]
MIN_IMAGE_PIXELS: Final[int] = 2500

MB: Final[int] = 1024 * 1024
MAX_SIZE: Final[int] = MB * 10
URL_TIMEOUT: Final[int] = 600
MIDDLEWARE_PARAMS: dict[str, Any] = {
    "allow_origins": ["*"],
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}

SUPPORTED_FORMATS = {
    "documents": {
        "PDF": ".pdf",
        "Microsoft Word": ".docx .doc",
        "Microsoft PowerPoint": ".pptx .ppt",
        "Microsoft Excel": ".xlsx .xls .xlsb",
        "OpenDocument": ".odt .odp .ods .odg",
        "HTML": ".html .htm",
        "XML": ".xml",
        "EPUB": ".epub",
        "Markdown": ".md .mdx .markdown",
        "RST": ".rst",
        "LaTeX": ".tex",
        "RTF": ".rtf",
        "Org": ".org",
    },
    "images": {
        "JPEG": ".jpg .jpeg",
        "PNG": ".png",
        "TIFF": ".tiff .tif",
        "BMP": ".bmp",
        "WebP": ".webp",
    },
    "email": {
        "EML": ".eml",
        "MSG": ".msg",
    },
    "text": {
        "Plain Text": ".txt .text",
        "CSV": ".csv",
        "TSV": ".tsv",
        "JSON": ".json",
    },
    "archives": {
        "ZIP": ".zip",
        "TAR": ".tar .tar.gz .tgz",
    },
}
