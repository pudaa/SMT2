from docx import Document
from docx.enum.style import WD_STYLE_TYPE
# Normal 是段落样式
# Header 是段落样式
# Header Char 是字符样式
# Footer 是段落样式
# Footer Char 是字符样式
# Heading 1 是段落样式
# Heading 2 是段落样式
# Heading 3 是段落样式
# Heading 4 是段落样式
# Heading 5 是段落样式
# Heading 6 是段落样式
# Heading 7 是段落样式
# Heading 8 是段落样式
# Heading 9 是段落样式
# Default Paragraph Font 是字符样式
# No Spacing 是段落样式
# Heading 1 Char 是字符样式
# Heading 2 Char 是字符样式
# Heading 3 Char 是字符样式
# Title 是段落样式
# Title Char 是字符样式
# Subtitle 是段落样式
# Subtitle Char 是字符样式
# List Paragraph 是段落样式
# Body Text 是段落样式
# Body Text Char 是字符样式
# Body Text 2 是段落样式
# Body Text 2 Char 是字符样式
# Body Text 3 是段落样式
# Body Text 3 Char 是字符样式
# List 是段落样式
# List 2 是段落样式
# List 3 是段落样式
# List Bullet 是段落样式
# List Bullet 2 是段落样式
# List Bullet 3 是段落样式
# List Number 是段落样式
# List Number 2 是段落样式
# List Number 3 是段落样式
# List Continue 是段落样式
# List Continue 2 是段落样式
# List Continue 3 是段落样式
# macro 是段落样式
# Macro Text Char 是字符样式
# Quote 是段落样式
# Quote Char 是字符样式
# Heading 4 Char 是字符样式
# Heading 5 Char 是字符样式
# Heading 6 Char 是字符样式
# Heading 7 Char 是字符样式
# Heading 8 Char 是字符样式
# Heading 9 Char 是字符样式
# Caption 是段落样式
# Strong 是字符样式
# Emphasis 是字符样式
# Intense Quote 是段落样式
# Intense Quote Char 是字符样式
# Subtle Emphasis 是字符样式
# Intense Emphasis 是字符样式
# Subtle Reference 是字符样式
# Intense Reference 是字符样式
# Book Title 是字符样式
# TOC Heading 是段落样式
doc = Document()
# 遍历所有的样式
for style in doc.styles:
    style_name = style.name
    style_type = style.type
    if style_type == WD_STYLE_TYPE.PARAGRAPH:
        print(f"{style_name} 是段落样式")
    elif style_type == WD_STYLE_TYPE.CHARACTER:
        print(f"{style_name} 是字符样式")
