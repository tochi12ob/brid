import logging
import openai
import tiktoken
from typing import Dict, List

from config import settings

class AIComplianceService:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.logger = logging.getLogger(__name__)

    def count_tokens(self, text: str) -> int:
        """Count tokens in a given text."""
        return len(self.tokenizer.encode(text))

    def truncate_text(self, text: str, max_tokens: int) -> str:
        """Truncate text to a specified token limit."""
        tokens = self.tokenizer.encode(text)
        if len(tokens) > max_tokens:
            return self.tokenizer.decode(tokens[:max_tokens])
        return text

    def analyze_compliance(
        self, 
        client_text: str, 
        benchmark_text: str, 
        max_tokens: int = 4096
    ) -> Dict[str, str]:
        """
        Perform AI-powered compliance analysis
        
        Args:
            client_text (str): Text to be analyzed
            benchmark_text (str): Benchmark policy text
            max_tokens (int): Maximum token limit
        
        Returns:
            Dict with compliance analysis results
        """
        try:
            # Truncate inputs to fit token limit
            client_text = self.truncate_text(client_text, max_tokens // 2)
            benchmark_text = self.truncate_text(benchmark_text, max_tokens // 2)

            prompt = f"""
            Compliance Analysis Task:
            
            Benchmark Policy:
            {benchmark_text}
            
            Client Policy:
            {client_text}
            
            Provide a detailed compliance analysis with:
            1. Overall Compliance Score (0-100%)
            2. Specific Compliance Gaps
            3. Detailed Recommendations
            4. Risk Assessment
            """

            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024
            )

            analysis_result = response.choices[0].message.content
            
            return self._parse_compliance_result(analysis_result)

        except Exception as e:
            self.logger.error(f"Compliance analysis error: {e}")
            return {
                "score": 0,
                "status": "Error",
                "details": str(e)
            }

    def _parse_compliance_result(self, result: str) -> Dict[str, str]:
        """
        Parse and structure compliance analysis result
        
        Args:
            result (str): Raw analysis text
        
        Returns:
            Structured compliance result
        """
        try:
            # Extract compliance score
            score_match = [
                float(word.rstrip('%')) 
                for word in result.split() 
                if word.rstrip('%').replace('.','').isdigit()
            ]
            score = score_match[0] if score_match else 50.0

            # Determine compliance status
            if score >= 90:
                status = "Fully Compliant"
            elif score >= 70:
                status = "Partially Compliant"
            else:
                status = "Non-Compliant"

            return {
                "score": score,
                "status": status,
                "details": result
            }

        except Exception as e:
            self.logger.error(f"Result parsing error: {e}")
            return {
                "score": 0,
                "status": "Error",
                "details": "Unable to parse analysis"
            }