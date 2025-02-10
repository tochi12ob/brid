import os
from dotenv import load_dotenv
import openai
from PyPDF2 import PdfReader
from rapidfuzz import process
import pandas as pd
import logging
from typing import List, Dict, Tuple, Optional
import tiktoken
import re
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from datetime import datetime
from pathlib import Path

# Load environment variables
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

class ComplianceService:
    def __init__(self, reports_dir: str = "reports"):
        """
        Initialize ComplianceService.
        
        Args:
            reports_dir (str): Directory to store PDF reports
        """
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger(__name__)
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(exist_ok=True)

    def preprocess_text(self, text: str) -> str:
        """Clean and preprocess text to reduce token count."""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[^\w\s.,;:?!()\-\'\"]+', ' ', text)
        return text.strip()

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using GPT-4's tokenizer."""
        encoder = tiktoken.encoding_for_model("gpt-4")
        return len(encoder.encode(text))

    def truncate_to_token_limit(self, text: str, max_tokens: int) -> str:
        """Truncate text to stay within token limit."""
        encoder = tiktoken.encoding_for_model("gpt-4")
        tokens = encoder.encode(text)
        if len(tokens) > max_tokens:
            return encoder.decode(tokens[:max_tokens])
        return text

    def split_into_chunks(self, text: str, max_tokens: int = 2000) -> List[str]:
        """Split text into chunks of specified token size."""
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            if sentence_tokens > max_tokens:
                words = sentence.split()
                temp_sentence = ""
                temp_tokens = 0
                
                for word in words:
                    word_tokens = self.count_tokens(word)
                    if temp_tokens + word_tokens > max_tokens:
                        chunks.append(temp_sentence)
                        temp_sentence = word
                        temp_tokens = word_tokens
                    else:
                        temp_sentence += " " + word if temp_sentence else word
                        temp_tokens += word_tokens
                
                if temp_sentence:
                    chunks.append(temp_sentence)
            
            elif current_tokens + sentence_tokens > max_tokens:
                chunks.append(current_chunk)
                current_chunk = sentence
                current_tokens = sentence_tokens
            else:
                current_chunk += " " + sentence if current_chunk else sentence
                current_tokens += sentence_tokens
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks

    def extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF file content."""
        text = ""
        reader = PdfReader(BytesIO(file_content))
        for page in reader.pages:
            text += page.extract_text()
        return self.preprocess_text(text)

    def define_requirements(self) -> List[Dict]:
        """Define the structured requirements categories."""
        return [
            {
                "category": "Documentation and Availability", 
                "text": "Framework must be well-documented and available to all relevant stakeholders"
            },
            {
                "category": "Roles and Responsibilities",
                "text": "Clear definition of roles, responsibilities, and accountability structures"
            },
            {
                "category": "Risk Assessment",
                "text": "Comprehensive risk assessment methodology and regular review processes"
            },
            {
                "category": "Security Controls",
                "text": "Implementation of appropriate technical and organizational security controls"
            },
            {
                "category": "Incident Response",
                "text": "Documented incident response procedures and reporting mechanisms"
            },
            {
                "category": "Compliance Monitoring",
                "text": "Regular monitoring and evaluation of compliance with requirements"
            }
        ]

    def check_compliance_with_retry(self, section: str, requirement: Dict, max_retries: int = 3) -> Dict:
        """Check compliance with retry logic and token limit handling."""
        MAX_TOTAL_TOKENS = 8000
        RESPONSE_TOKENS = 500
        PROMPT_TEMPLATE_TOKENS = 150
        MAX_CONTENT_TOKENS = MAX_TOTAL_TOKENS - RESPONSE_TOKENS - PROMPT_TEMPLATE_TOKENS
        
        section = self.truncate_to_token_limit(section, int(MAX_CONTENT_TOKENS * 0.7))
        requirement_text = self.truncate_to_token_limit(requirement['text'], int(MAX_CONTENT_TOKENS * 0.3))
        
        prompt = f"""As a compliance auditor, analyze this policy section against the requirement and provide your analysis in the following format:
        - Score: A number between 0-100
        - Analysis: A brief analysis of alignment
        - Recommendations: Specific recommendations for improvement

        Section: {section}
        Requirement Category: {requirement['category']}
        Specific Requirement: {requirement_text}"""
        
        for attempt in range(max_retries):
            try:
                response = openai.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=RESPONSE_TOKENS
                )
                
                # Parse the response text to extract structured data
                response_text = response.choices[0].message.content
                
                # Simple parsing logic for demonstration
                score_match = re.search(r'Score:\s*(\d+)', response_text)
                analysis_match = re.search(r'Analysis:\s*(.+?)(?=Recommendations:|$)', response_text, re.DOTALL)
                recommendations_match = re.search(r'Recommendations:\s*(.+)$', response_text, re.DOTALL)
                
                return {
                    "score": float(score_match.group(1)) if score_match else 0,
                    "analysis": analysis_match.group(1).strip() if analysis_match else "No analysis provided",
                    "recommendations": recommendations_match.group(1).strip() if recommendations_match else "No recommendations provided"
                }
                
            except Exception as e:
                if attempt == max_retries - 1:
                    self.logger.error(f"Final error during OpenAI API call: {e}")
                    return {
                        "score": 0,
                        "analysis": f"Error: {str(e)}",
                        "recommendations": "Unable to process"
                    }
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
        
        return {
            "score": 0,
            "analysis": "Maximum retries exceeded",
            "recommendations": "System error"
        }

    def process_policy_chunk(self, chunk: str, requirements: List[Dict], chunk_index: int, total_chunks: int) -> List[Dict]:
        """Process a single chunk of policy text against requirements."""
        results = []
        self.logger.info(f"Processing chunk {chunk_index}/{total_chunks}")
        
        for req in requirements:
            chunk_sections = chunk.split('\n\n')
            best_match = self.find_best_match(req['text'], chunk_sections)
            
            if best_match[0] and best_match[1] > 50:
                compliance_result = self.check_compliance_with_retry(best_match[0], req)
                results.append({
                    "category": req["category"],
                    "score": compliance_result.get("score", 0),
                    "analysis": compliance_result.get("analysis", ""),
                    "recommendations": compliance_result.get("recommendations", "")
                })
        
        return results

    def find_best_match(self, text: str, candidates: List[str]) -> tuple:
        """Find best matching text from candidates using fuzzy matching."""
        if not candidates:
            return (None, 0)
        text = self.preprocess_text(text)
        candidates = [self.preprocess_text(c) for c in candidates]
        best_match, score, _ = process.extractOne(text, candidates)
        return (best_match, score) if score >= 50 else (None, 0)

    def generate_report_paths(self, file_name: str) -> Path:
        """Generate paths for storing reports."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        base_name = Path(file_name).stem
        pdf_name = f"{base_name}_{timestamp}.pdf"
        return self.reports_dir / pdf_name

    def create_pdf_report(self, results: List[Dict], overall_score: float) -> BytesIO:
        """Create a PDF report from the analysis results."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        styles = getSampleStyleSheet()
        elements = []
        
        # Define custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=12,
            textColor=colors.HexColor('#2F4F4F')
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            spaceBefore=6,
            spaceAfter=6
        )
        
        # Add title
        elements.append(Paragraph("Policy Compliance Analysis Report", title_style))
        elements.append(Spacer(1, 20))
        
        # Add overall score
        elements.append(Paragraph(f"Overall Compliance Score: {overall_score:.1f}%", heading_style))
        elements.append(Spacer(1, 20))
        
        # Add detailed results
        for result in results:
            elements.append(Paragraph(result['category'], heading_style))
            elements.append(Spacer(1, 10))
            
            elements.append(Paragraph(f"Score: {result['score']}%", body_style))
            elements.append(Spacer(1, 5))
            
            elements.append(Paragraph("Analysis:", body_style))
            elements.append(Paragraph(result['analysis'], body_style))
            elements.append(Spacer(1, 5))
            
            elements.append(Paragraph("Recommendations:", body_style))
            elements.append(Paragraph(result['recommendations'], body_style))
            elements.append(Spacer(1, 15))
        
        try:
            doc.build(elements)
            buffer.seek(0)
            return buffer
        except Exception as e:
            self.logger.error(f"Error generating PDF report: {str(e)}")
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = [
                Paragraph("Error Generating Report", styles['Heading1']),
                Paragraph(f"An error occurred while generating the report: {str(e)}", styles['Normal'])
            ]
            doc.build(elements)
            buffer.seek(0)
            return buffer

    def format_markdown_report(self, results: List[Dict], overall_score: float, max_length: int = 5000) -> str:
        """Format results as a markdown report with length limit."""
        markdown = f"# Policy Compliance Analysis Report\n\n"
        markdown += f"## Overall Score: {overall_score:.1f}%\n\n"
        
        for result in results:
            markdown += f"## {result['category']}\n\n"
            markdown += f"**Score:** {result['score']}%\n\n"
            
            # Truncate analysis and recommendations
            analysis = result['analysis'][:1000]  # Limit to 1000 characters
            recommendations = result['recommendations'][:1000]
            
            markdown += f"**Analysis:**\n{analysis}\n\n"
            markdown += f"**Recommendations:**\n{recommendations}\n\n"
            markdown += "---\n\n"
        
        # Ensure total markdown doesn't exceed max_length
        return markdown[:max_length]

    def analyze_policy(self, file_content: bytes, user_id: int, file_name: str) -> Dict:
        """
        Analyze policy document and prepare database record.
        """
        try:
            # Extract and process text
            client_policy_text = self.extract_text_from_pdf(file_content)
            client_policy_text = self.preprocess_text(client_policy_text)
            chunks = self.split_into_chunks(client_policy_text, 2000)
            requirements = self.define_requirements()
            
            # Process chunks
            all_results = []
            for i, chunk in enumerate(chunks, 1):
                chunk_results = self.process_policy_chunk(chunk, requirements, i, len(chunks))
                all_results.extend(chunk_results)
            
            # Consolidate results
            consolidated_results = {}
            for result in all_results:
                category = result["category"]
                if category not in consolidated_results or result["score"] > consolidated_results[category]["score"]:
                    consolidated_results[category] = result
            
            final_results = list(consolidated_results.values())
            overall_score = sum(r["score"] for r in final_results) / len(final_results) if final_results else 0
            
            # Generate reports with length limit
            pdf_buffer = self.create_pdf_report(final_results, overall_score)
            markdown_report = self.format_markdown_report(final_results, overall_score, max_length=5000)
            
            # Log a warning if truncation occurred
            if len(markdown_report) >= 5000:
                self.logger.warning(f"Markdown report for {file_name} was truncated")
            
            # Save PDF report
            pdf_path = self.generate_report_paths(file_name)
            with open(pdf_path, 'wb') as f:
                f.write(pdf_buffer.getvalue())
            
            # Calculate compliance status
            if overall_score >= 80:
                compliance_status = "Compliant"
            elif overall_score >= 60:
                compliance_status = "Partially Compliant"
            else:
                compliance_status = "Non-Compliant"
            
            # Prepare database record
            db_record = {
                "user_id": user_id,
                "file_name": file_name,
                "overall_score": overall_score,
                "markdown_report": markdown_report,
                "pdf_report": str(pdf_path),
                "compliance_status": compliance_status,
                "created_at": datetime.utcnow()
            }

            return db_record
            
        except Exception as e:
            self.logger.error(f"Error in policy analysis: {str(e)}")
            raise