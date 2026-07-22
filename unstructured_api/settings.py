PDF_IMAGE_DPI = 200
EXTRACT_IMAGE_BLOCK_TYPES = ["Image", "Table"]
MIN_IMAGE_PIXELS = 2500

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
