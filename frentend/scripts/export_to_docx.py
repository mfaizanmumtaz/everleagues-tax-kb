"""
Export Markdown File to DOCX
Converts client_requirements_scope_analysis.md to Word document format
"""

import os
import sys
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
import re

def setup_document_styles(doc):
    """Setup custom styles for the document"""
    styles = doc.styles
    
    # Heading 1 style
    if 'Custom Heading 1' not in [s.name for s in styles]:
        h1_style = styles.add_style('Custom Heading 1', WD_STYLE_TYPE.PARAGRAPH)
        h1_format = h1_style.font
        h1_format.name = 'Calibri'
        h1_format.size = Pt(18)
        h1_format.bold = True
        h1_format.color = RGBColor(31, 78, 121)
        h1_style.paragraph_format.space_after = Pt(12)
    
    # Heading 2 style
    if 'Custom Heading 2' not in [s.name for s in styles]:
        h2_style = styles.add_style('Custom Heading 2', WD_STYLE_TYPE.PARAGRAPH)
        h2_format = h2_style.font
        h2_format.name = 'Calibri'
        h2_format.size = Pt(14)
        h2_format.bold = True
        h2_format.color = RGBColor(68, 114, 196)
        h2_style.paragraph_format.space_before = Pt(12)
        h2_style.paragraph_format.space_after = Pt(8)
    
    # Heading 3 style
    if 'Custom Heading 3' not in [s.name for s in styles]:
        h3_style = styles.add_style('Custom Heading 3', WD_STYLE_TYPE.PARAGRAPH)
        h3_format = h3_style.font
        h3_format.name = 'Calibri'
        h3_format.size = Pt(12)
        h3_format.bold = True
        h3_format.color = RGBColor(112, 173, 71)
        h3_style.paragraph_format.space_before = Pt(10)
        h3_style.paragraph_format.space_after = Pt(6)
    
    # Table Header style
    if 'Custom Table Header' not in [s.name for s in styles]:
        th_style = styles.add_style('Custom Table Header', WD_STYLE_TYPE.PARAGRAPH)
        th_format = th_style.font
        th_format.name = 'Calibri'
        th_format.size = Pt(10)
        th_format.bold = True
        th_format.color = RGBColor(255, 255, 255)

def parse_markdown_to_docx(md_file_path, docx_file_path):
    """Parse markdown file and convert to DOCX"""
    
    # Read markdown file
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create document
    doc = Document()
    setup_document_styles(doc)
    
    # Set document margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
    
    # Split content into lines
    lines = content.split('\n')
    
    i = 0
    current_table = None
    current_table_rows = []
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines (but add spacing)
        if not line:
            i += 1
            continue
        
        # Heading 1 (# Title)
        if line.startswith('# '):
            title = line[2:].strip()
            p = doc.add_paragraph(title)
            p.style = 'Custom Heading 1'
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        # Heading 2 (## Title)
        elif line.startswith('## '):
            title = line[3:].strip()
            # Remove markdown links if present
            title = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', title)
            p = doc.add_paragraph(title)
            p.style = 'Custom Heading 2'
        
        # Heading 3 (### Title)
        elif line.startswith('### '):
            title = line[4:].strip()
            p = doc.add_paragraph(title)
            p.style = 'Custom Heading 3'
        
        # Horizontal rule (---)
        elif line.startswith('---'):
            p = doc.add_paragraph()
            p_format = p.paragraph_format
            p_format.space_after = Pt(12)
        
        # Table row (starts with |)
        elif line.startswith('|') and '|' in line[1:]:
            # Start of new table or continuation
            if current_table is None:
                # Parse header row
                headers = [cell.strip() for cell in line.split('|')[1:-1]]
                if len(headers) > 0 and headers[0]:  # Valid table
                    current_table = doc.add_table(rows=1, cols=len(headers))
                    current_table.style = 'Light Grid Accent 1'
                    
                    # Add header row
                    header_cells = current_table.rows[0].cells
                    for j, header in enumerate(headers):
                        header_cells[j].text = header.strip()
                        # Format header cells
                        for paragraph in header_cells[j].paragraphs:
                            paragraph.style = 'Custom Table Header'
                            for run in paragraph.runs:
                                run.font.bold = True
                    
                    current_table_rows = []
            else:
                # Data row
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                if len(cells) == len(current_table.columns):
                    row_cells = current_table.add_row().cells
                    for j, cell_text in enumerate(cells):
                        row_cells[j].text = cell_text
                        # Format code/technical terms
                        if cell_text in ['WITHIN SCOPE', 'OUT OF SCOPE']:
                            for paragraph in row_cells[j].paragraphs:
                                for run in paragraph.runs:
                                    run.font.bold = True
                                    if cell_text == 'WITHIN SCOPE':
                                        run.font.color.rgb = RGBColor(112, 173, 71)
                                    else:
                                        run.font.color.rgb = RGBColor(192, 0, 0)
            
            # Check if next line is separator row (|---|---|)
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line.startswith('|---'):
                    i += 1  # Skip separator
                    continue
        
        # Blockquote (> text)
        elif line.startswith('> '):
            text = line[2:].strip()
            # Remove **bold** markers if present
            text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
            p = doc.add_paragraph(text, style='Intense Quote')
            for run in p.runs:
                run.font.italic = True
                run.font.color.rgb = RGBColor(89, 89, 89)
        
        # Bullet list (- item)
        elif line.startswith('- '):
            text = line[2:].strip()
            # Remove markdown formatting
            text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
            text = re.sub(r'`([^`]+)`', r'\1', text)
            p = doc.add_paragraph(text, style='List Bullet')
        
        # Numbered list (1. item or #. item)
        elif re.match(r'^\d+\.\s', line) or re.match(r'^#\.\s', line):
            text = re.sub(r'^\d+\.\s', '', line)
            text = re.sub(r'^#\.\s', '', text)
            text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
            p = doc.add_paragraph(text, style='List Number')
        
        # Code block (```)
        elif line.startswith('```'):
            # Skip code block for now, or you can handle it differently
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            if code_lines:
                p = doc.add_paragraph('\n'.join(code_lines))
                p.style = 'No Spacing'
                for run in p.runs:
                    run.font.name = 'Courier New'
                    run.font.size = Pt(9)
                    run.font.color.rgb = RGBColor(0, 0, 139)
            i += 1
            continue
        
        # Inline code (`code`)
        elif '`' in line:
            # Handle inline code
            parts = re.split(r'`([^`]+)`', line)
            p = doc.add_paragraph()
            for part in parts:
                if parts.index(part) % 2 == 1:  # Code part
                    run = p.add_run(part)
                    run.font.name = 'Courier New'
                    run.font.size = Pt(10)
                    run.font.color.rgb = RGBColor(0, 0, 139)
                else:  # Regular text
                    clean_text = part
                    clean_text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', clean_text)
                    p.add_run(clean_text)
        else:
            # Regular paragraph
            text = line
            # Clean markdown formatting
            text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)  # Bold
            text = re.sub(r'\*([^\*]+)\*', r'\1', text)  # Italic
            text = re.sub(r'`([^`]+)`', r'\1', text)  # Inline code
            text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Links
            
            # Check if this is a table separator (|---|---|)
            if re.match(r'^\|[\s\-:]+\|', text):
                # End of current table
                if current_table:
                    current_table = None
                    current_table_rows = []
                    doc.add_paragraph()  # Add space after table
                i += 1
                continue
            
            # Only add paragraph if not empty after cleaning
            if text.strip():
                p = doc.add_paragraph(text)
        
        i += 1
    
    # Finalize last table if exists
    if current_table:
        doc.add_paragraph()  # Add space after table
    
    # Save document
    doc.save(docx_file_path)
    print(f"Successfully exported to: {docx_file_path}")

def main():
    """Main function"""
    # Get project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Define input and output paths
    md_file = project_root / "project_documents" / "client_requirements_scope_analysis.md"
    docx_file = project_root / "project_documents" / "client_requirements_scope_analysis.docx"
    
    # Check if markdown file exists
    if not md_file.exists():
        print(f"Error: Markdown file not found at {md_file}")
        sys.exit(1)
    
    # Convert to DOCX
    try:
        parse_markdown_to_docx(str(md_file), str(docx_file))
        print(f"\nExport completed successfully!")
        print(f"Input:  {md_file}")
        print(f"Output: {docx_file}")
    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

