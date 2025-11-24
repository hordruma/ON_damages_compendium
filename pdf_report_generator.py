"""
PDF Report Generator
Creates professional PDF reports from search results
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from datetime import datetime
from typing import List, Dict, Optional
import numpy as np


class DamagesReportGenerator:
    """Generates professional PDF reports for damages analysis"""

    def __init__(self, output_path: str, pagesize=letter):
        """
        Initialize the report generator

        Args:
            output_path: Path where PDF will be saved
            pagesize: Page size (letter or A4)
        """
        self.output_path = output_path
        self.pagesize = pagesize
        self.doc = SimpleDocTemplate(
            output_path,
            pagesize=pagesize,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self.story = []

    def _setup_custom_styles(self):
        """Create custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f2937'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Section header
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#3b82f6'),
            spaceAfter=12,
            spaceBefore=16,
            fontName='Helvetica-Bold'
        ))

        # Case title
        self.styles.add(ParagraphStyle(
            name='CaseTitle',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#1f2937'),
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))

        # Summary box
        self.styles.add(ParagraphStyle(
            name='SummaryBox',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#059669'),
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))

        # Metadata
        self.styles.add(ParagraphStyle(
            name='Metadata',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6b7280'),
            alignment=TA_CENTER
        ))

    def add_header(
        self,
        title: str = "Ontario Damages Comparator",
        subtitle: str = "Case Analysis Report"
    ):
        """Add report header"""
        self.story.append(Paragraph(title, self.styles['CustomTitle']))
        self.story.append(Paragraph(subtitle, self.styles['Heading2']))
        self.story.append(Spacer(1, 0.2*inch))

        # Metadata
        date_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        self.story.append(
            Paragraph(f"Generated: {date_str}", self.styles['Metadata'])
        )
        self.story.append(Spacer(1, 0.3*inch))

    def add_search_parameters(
        self,
        selected_regions: List[str],
        region_labels: Dict[str, str],
        injury_description: str,
        gender: Optional[str] = None,
        age: Optional[int] = None
    ):
        """Add search parameters section"""
        self.story.append(
            Paragraph("Search Parameters", self.styles['SectionHeader'])
        )

        # Demographics
        demo_data = []
        if gender and gender != "Not Specified":
            demo_data.append(["Gender:", gender])
        if age:
            demo_data.append(["Age:", str(age)])

        if demo_data:
            demo_table = Table(demo_data, colWidths=[1.5*inch, 4*inch])
            demo_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1f2937')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            self.story.append(demo_table)
            self.story.append(Spacer(1, 0.1*inch))

        # Injured regions
        if selected_regions:
            self.story.append(
                Paragraph("<b>Injured Regions:</b>", self.styles['Normal'])
            )

            regions_text = "<br/>".join([
                f"• {region_labels.get(r, r)}"
                for r in selected_regions
            ])
            self.story.append(
                Paragraph(regions_text, self.styles['Normal'])
            )
            self.story.append(Spacer(1, 0.1*inch))

        # Injury description
        self.story.append(
            Paragraph("<b>Injury Description:</b>", self.styles['Normal'])
        )
        self.story.append(
            Paragraph(injury_description, self.styles['Normal'])
        )
        self.story.append(Spacer(1, 0.2*inch))

    def add_damage_summary(self, damages_values: List[float]):
        """Add damage award summary statistics"""
        if not damages_values:
            return

        self.story.append(
            Paragraph("Damage Award Summary", self.styles['SectionHeader'])
        )

        median_val = np.median(damages_values)
        min_val = np.min(damages_values)
        max_val = np.max(damages_values)
        mean_val = np.mean(damages_values)

        summary_data = [
            ['Statistic', 'Amount'],
            ['Median Award', f'${median_val:,.0f}'],
            ['Mean Award', f'${mean_val:,.0f}'],
            ['Minimum Award', f'${min_val:,.0f}'],
            ['Maximum Award', f'${max_val:,.0f}'],
            ['Number of Cases', str(len(damages_values))]
        ]

        summary_table = Table(summary_data, colWidths=[2.5*inch, 2.5*inch])
        summary_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # Data rows
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f3f4f6')),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),

            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.HexColor('#f9fafb'), colors.HexColor('#f3f4f6')]),
        ]))

        self.story.append(summary_table)
        self.story.append(Spacer(1, 0.3*inch))

    def add_comparable_cases(
        self,
        results: List[tuple],
        max_cases: int = 10
    ):
        """
        Add comparable cases section

        Args:
            results: List of (case, embedding_sim, combined_score) tuples
            max_cases: Maximum number of cases to include
        """
        self.story.append(
            Paragraph("Comparable Cases", self.styles['SectionHeader'])
        )

        self.story.append(
            Paragraph(
                f"Top {min(len(results), max_cases)} most similar cases based on injury description and affected regions:",
                self.styles['Normal']
            )
        )
        self.story.append(Spacer(1, 0.15*inch))

        for idx, (case, emb_sim, combined_score) in enumerate(results[:max_cases], 1):
            case_elements = []

            # Case title
            case_name = case.get('case_name', 'Unknown Case')
            year = case.get('year', '')
            court = case.get('court', '')

            title_text = f"<b>Case {idx}: {case_name}</b>"
            if year:
                title_text += f" ({year})"

            case_elements.append(
                Paragraph(title_text, self.styles['CaseTitle'])
            )

            # Case details table
            details = []

            if case.get('region'):
                details.append(['Region:', case['region']])

            if court:
                details.append(['Court:', court])

            if case.get('damages'):
                details.append([
                    'Damages:',
                    f"${case['damages']:,.0f}"
                ])

            details.append([
                'Match Score:',
                f"{combined_score*100:.1f}%"
            ])

            if details:
                details_table = Table(details, colWidths=[1.2*inch, 4*inch])
                details_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTNAME', (1, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]))
                case_elements.append(details_table)

            # Case summary
            summary = case.get('summary_text', '')
            if summary:
                summary_text = summary[:400] + ("..." if len(summary) > 400 else "")
                case_elements.append(Spacer(1, 0.05*inch))
                case_elements.append(
                    Paragraph(f"<i>{summary_text}</i>", self.styles['Normal'])
                )

            # Keep case together on same page
            self.story.append(KeepTogether(case_elements))
            self.story.append(Spacer(1, 0.15*inch))

            # Add divider
            if idx < min(len(results), max_cases):
                self.story.append(
                    Table(
                        [['']],
                        colWidths=[6.5*inch],
                        style=[
                            ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.HexColor('#e5e7eb'))
                        ]
                    )
                )
                self.story.append(Spacer(1, 0.15*inch))

    def add_disclaimer(self):
        """Add legal disclaimer"""
        self.story.append(PageBreak())
        self.story.append(
            Paragraph("Important Disclaimer", self.styles['SectionHeader'])
        )

        disclaimer_text = """
        <b>This report is provided for reference purposes only.</b><br/><br/>

        The case comparisons and damage award estimates contained in this report are based on
        automated analysis of the Ontario Damages Compendium and should not be considered
        legal advice or a definitive valuation of any claim.<br/><br/>

        <b>Important considerations:</b><br/>
        • Each case is unique and depends on specific facts and circumstances<br/>
        • Damage awards vary based on numerous factors including plaintiff age, severity of injury,
          impact on employment, jurisdiction, and trial vs. settlement context<br/>
        • This tool uses AI-powered semantic matching which may not capture all relevant nuances<br/>
        • All case references should be independently verified against primary sources<br/>
        • This analysis does not constitute legal advice<br/>
        • Users should consult with qualified legal professionals for case-specific guidance<br/><br/>

        <b>Data Source:</b> Canadian Case Law Association (CCLA) Damages Compendium 2024<br/><br/>

        © 2024 Ontario Damages Comparator Tool
        """

        self.story.append(
            Paragraph(disclaimer_text, self.styles['Normal'])
        )

    def generate(self):
        """Build and save the PDF"""
        self.doc.build(self.story)
        return self.output_path


def generate_damages_report(
    output_path: str,
    selected_regions: List[str],
    region_labels: Dict[str, str],
    injury_description: str,
    results: List[tuple],
    damages_values: List[float],
    gender: Optional[str] = None,
    age: Optional[int] = None,
    max_cases: int = 10
) -> str:
    """
    Convenience function to generate a complete damages report

    Args:
        output_path: Where to save the PDF
        selected_regions: List of region IDs
        region_labels: Map of region IDs to clinical labels
        injury_description: User's injury description
        results: Search results (case, emb_sim, combined_score) tuples
        damages_values: List of damage award values
        gender: Plaintiff gender (optional)
        age: Plaintiff age (optional)
        max_cases: Maximum cases to include in report

    Returns:
        Path to generated PDF
    """
    generator = DamagesReportGenerator(output_path)

    generator.add_header()
    generator.add_search_parameters(
        selected_regions,
        region_labels,
        injury_description,
        gender,
        age
    )
    generator.add_damage_summary(damages_values)
    generator.add_comparable_cases(results, max_cases)
    generator.add_disclaimer()

    return generator.generate()
