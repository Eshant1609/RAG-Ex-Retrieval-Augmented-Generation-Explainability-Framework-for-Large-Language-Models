import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
import uuid
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER

from utils.config import Config

logger = logging.getLogger(__name__)

class ExportService:
    """Handle export of summaries and documents in various formats"""
    
    def __init__(self):
        self.summaries_folder = Config.SUMMARIES_FOLDER
        self.export_folder = Config.EXPORT_FOLDER
        os.makedirs(self.summaries_folder, exist_ok=True)
        os.makedirs(self.export_folder, exist_ok=True)
    
    def save_summary(self, summary: str, metadata: Dict) -> str:
        """Save a generated summary"""
        summary_id = str(uuid.uuid4())
        summary_data = {
            'summary_id': summary_id,
            'summary': summary,
            'metadata': metadata,
            'created_at': datetime.now().isoformat()
        }
        
        summary_file = os.path.join(self.summaries_folder, f"{summary_id}.json")
        try:
            with open(summary_file, 'w') as f:
                json.dump(summary_data, f, indent=2)
            return summary_id
        except Exception as e:
            logger.error(f"Error saving summary: {str(e)}")
            raise
    
    def get_summary(self, summary_id: str) -> Optional[Dict]:
        """Get a saved summary"""
        summary_file = os.path.join(self.summaries_folder, f"{summary_id}.json")
        try:
            if os.path.exists(summary_file):
                with open(summary_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading summary: {str(e)}")
        return None
    
    def list_summaries(self) -> List[Dict]:
        """List all saved summaries"""
        summaries = []
        try:
            for filename in os.listdir(self.summaries_folder):
                if filename.endswith('.json'):
                    summary_id = filename[:-5]
                    summary = self.get_summary(summary_id)
                    if summary:
                        summaries.append({
                            'summary_id': summary_id,
                            'preview': summary['summary'][:200] + '...' if len(summary['summary']) > 200 else summary['summary'],
                            'created_at': summary.get('created_at', ''),
                            'metadata': summary.get('metadata', {})
                        })
            
            # Sort by creation date (newest first)
            summaries.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        except Exception as e:
            logger.error(f"Error listing summaries: {str(e)}")
        
        return summaries
    
    def export(self, export_type: str, summary_id: Optional[str] = None, document_ids: Optional[List[str]] = None) -> Optional[str]:
        """
        Export data in specified format
        
        Args:
            export_type: 'markdown', 'json', or 'pdf'
            summary_id: ID of summary to export
            document_ids: List of document IDs to export
            
        Returns:
            Path to exported file
        """
        try:
            if summary_id:
                return self._export_summary(export_type, summary_id)
            elif document_ids:
                return self._export_documents(export_type, document_ids)
            else:
                return None
        except Exception as e:
            logger.error(f"Error exporting: {str(e)}")
            return None
    
    def _export_summary(self, export_type: str, summary_id: str) -> Optional[str]:
        """Export a summary"""
        summary = self.get_summary(summary_id)
        if not summary:
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if export_type == 'markdown':
            filename = f"summary_{summary_id[:8]}_{timestamp}.md"
            filepath = os.path.join(self.export_folder, filename)
            
            content = self._format_summary_markdown(summary)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return filepath
        
        elif export_type == 'json':
            filename = f"summary_{summary_id[:8]}_{timestamp}.json"
            filepath = os.path.join(self.export_folder, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            return filepath
        
        elif export_type == 'pdf':
            filename = f"summary_{summary_id[:8]}_{timestamp}.pdf"
            filepath = os.path.join(self.export_folder, filename)
            
            self._export_summary_pdf(summary, filepath)
            return filepath
        
        return None
    
    def _export_documents(self, export_type: str, document_ids: List[str]) -> Optional[str]:
        """Export documents (not fully implemented, placeholder)"""
        # This would require access to vector_store, so it's a placeholder
        # In a full implementation, you'd retrieve document text and export it
        logger.warning("Document export not fully implemented")
        return None
    
    def _format_summary_markdown(self, summary: Dict) -> str:
        """Format summary as markdown"""
        metadata = summary.get('metadata', {})
        sources = metadata.get('sources', [])
        
        content = f"""# Research Summary

**Generated:** {summary.get('created_at', 'Unknown')}

## Summary

{summary.get('summary', '')}

## Sources

"""
        
        if sources:
            for i, source in enumerate(sources, 1):
                content += f"{i}. **{source.get('title', 'Unknown')}** ({source.get('filename', 'Unknown')})\n"
        else:
            content += "No sources available.\n"
        
        if metadata.get('query'):
            content += f"\n## Query\n\n{metadata.get('query')}\n"
        
        return content
    
    def _export_summary_pdf(self, summary: Dict, filepath: str):
        """Export summary as PDF"""
        try:
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor='#1a1a1a',
                spaceAfter=30,
                alignment=TA_CENTER
            )
            story.append(Paragraph("Research Summary", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Date
            date_str = summary.get('created_at', 'Unknown')
            story.append(Paragraph(f"<b>Generated:</b> {date_str}", styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
            
            # Summary
            story.append(Paragraph("<b>Summary</b>", styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))
            
            summary_text = summary.get('summary', '').replace('\n', '<br/>')
            story.append(Paragraph(summary_text, styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
            
            # Sources
            metadata = summary.get('metadata', {})
            sources = metadata.get('sources', [])
            
            if sources:
                story.append(Paragraph("<b>Sources</b>", styles['Heading2']))
                story.append(Spacer(1, 0.1*inch))
                
                for i, source in enumerate(sources, 1):
                    source_text = f"{i}. {source.get('title', 'Unknown')} ({source.get('filename', 'Unknown')})"
                    story.append(Paragraph(source_text, styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
            
            # Query if available
            if metadata.get('query'):
                story.append(Spacer(1, 0.2*inch))
                story.append(Paragraph("<b>Query</b>", styles['Heading2']))
                story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph(metadata.get('query'), styles['Normal']))
            
            doc.build(story)
            
        except Exception as e:
            logger.error(f"Error creating PDF: {str(e)}")
            raise

