# Markdown to DOCX Export Script

This script converts `client_requirements_scope_analysis.md` to a Microsoft Word (.docx) document.

## Installation

1. Install Python 3.7 or higher if not already installed.

2. Install required dependencies:
```bash
pip install -r requirements_export.txt
```

Or install directly:
```bash
pip install python-docx
```

## Usage

### Option 1: Run from command line

```bash
cd scripts
python export_to_docx.py
```

### Option 2: Run from project root

```bash
python scripts/export_to_docx.py
```

## Output

The script will generate:
- **Output file:** `project_documents/client_requirements_scope_analysis.docx`
- **Input file:** `project_documents/client_requirements_scope_analysis.md`

## Features

The script converts markdown elements to Word format:

- **Headings** (# ## ###) → Word heading styles with custom formatting
- **Tables** (| col1 | col2 |) → Word tables with styled headers
- **Lists** (- item, 1. item) → Word bullet/numbered lists
- **Bold/Italic** (**text**, *text*) → Word formatting
- **Code blocks** (```code```) → Monospace font
- **Blockquotes** (> text) → Italic quote style
- **Scope flags** → Color-coded (Green for WITHIN SCOPE, Red for OUT OF SCOPE)

## Customization

You can modify the script to:
- Change document margins (section.top_margin, etc.)
- Adjust heading colors and sizes
- Change table styles
- Modify font families

Edit the `setup_document_styles()` function in `export_to_docx.py`.

## Troubleshooting

### Error: "ModuleNotFoundError: No module named 'docx'"
**Solution:** Install python-docx:
```bash
pip install python-docx
```

### Error: "File not found"
**Solution:** Make sure you're running the script from the correct directory, or the markdown file exists at:
```
project_documents/client_requirements_scope_analysis.md
```

### Tables not formatting correctly
**Solution:** The script tries to detect markdown tables automatically. If tables aren't converting properly, check that your markdown uses proper table syntax:
```markdown
| Header 1 | Header 2 |
|----------|----------|
| Data 1   | Data 2   |
```

## Notes

- The script preserves most markdown formatting but may require manual adjustments for complex layouts
- Code blocks are converted to monospace text but may not preserve syntax highlighting
- Very large documents may take a few seconds to process

