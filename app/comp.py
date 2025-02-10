# app/services/compliance_ai_service.py
import logging
import openai
import tiktoken
from typing import List, Dict, Any

class ComplianceAIService:
    def __init__(self, api_key: str):
        openai.api_key = api_key
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))
    
    def truncate_text(self, text: str, max_tokens: int) -> str:
        tokens = self.tokenizer.encode(text)
        if len(tokens) > max_tokens:
            return self.tokenizer.decode(tokens[:max_tokens])
        return text
    
    def generate_suggestions(self, requirement: str, client_section: str) -> Dict[str, Any]:
        prompt_template = f"""
        You are a compliance auditor. Compare the following policy section against the benchmark requirement:

        Policy Section:
        {client_section}

        Requirement:
        "{requirement}"

        Provide:
        1. Whether the requirement is met ('Yes', 'Partially', or 'No')
        2. Percentage of compliance
        3. Specific missing clauses
        4. Clear, actionable recommendations
        5. Headings for non-compliant sections
        6. Percentage score for each section
        """

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt_template}]
            )
            
            result = response.choices[0].message.content
            return self._parse_compliance_result(result)
        
        except Exception as e:
            logging.error(f"AI Analysis Error: {e}")
            return {"result": "Error in analysis", "score": 0}
    
    def _parse_compliance_result(self, result: str) -> Dict[str, Any]:
        score = 0
        if "Yes" in result:
            score = 100  # Fully compliant
        elif "Partially" in result:
            try:
                partial_score = [int(s.strip('%')) for s in result.split() if s.endswith('%')]
                score = partial_score[0] if partial_score else 50
            except:
                score = 50  # Default partial score
        
        return {
            "result": result.strip(),
            "score": score
        }
    
    def policy_compliance_check(
        self, 
        client_policy_texts: List[str], 
        company_policy_text: str
    ) -> Dict[str, Any]:
        compliant_sections = []
        non_compliant_sections = []
        total_score = 0
        total_requirements = 0

        # Split policies into sections
        def split_sections(text):
            return [section.strip() for section in text.split("\n\n") if section.strip()]

        client_policy_sections = [split_sections(policy) for policy in client_policy_texts]
        company_policy_sections = split_sections(company_policy_text)

        for requirement_chunk in company_policy_sections:
            total_requirements += 1
            for client_policy_section in client_policy_sections:
                for client_chunk in client_policy_section:
                    try:
                        result = self.generate_suggestions(requirement_chunk, client_chunk)
                        score = result["score"]

                        if score == 100:
                            compliant_sections.append({
                                'requirement': requirement_chunk,
                                'score': score,
                                'explanation': result['result']
                            })
                        else:
                            non_compliant_sections.append({
                                'requirement': requirement_chunk,
                                'score': score,
                                'explanation': result['result']
                            })

                        total_score += score
                    except Exception as e:
                        logging.error(f"Error processing requirement: {e}")

        overall_score = (total_score / total_requirements) if total_requirements > 0 else 0
        
        return {
            "overall_score": overall_score,
            "compliant_sections": compliant_sections,
            "non_compliant_sections": non_compliant_sections
        }

