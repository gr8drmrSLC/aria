"""
ARIA Analyst Module
This module provides the Analyst class for evaluating research papers using Anthropic's Claude API.
It also includes utility functions for domain-specific filtering.
"""

import os
import logging
import json
from typing import List, Dict
import anthropic

logger = logging.getLogger('aria.analyst')

class Analyst:
    def __init__(self):
        """Initializes the Analyst with API configuration from environment variables."""
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.model = os.getenv("ARIA_MODEL", "claude-sonnet-4-6")
        self.threshold = int(os.getenv("ARIA_NOVELTY_THRESHOLD", "7"))
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def analyze_papers(self, papers: List[Dict]) -> List[Dict]:
        """
        Analyzes a list of papers using the Claude API in batches of up to 10.
        Adds novelty_score, themes, is_notable, and rationale to each paper.
        """
        if not papers:
            return []

        analyzed_papers = []
        batch_size = 10
        
        system_prompt = (
            "You are a research intelligence analyst for ARIA (Autonomous Research Intelligence Agent). "
            "Your task is to analyze scientific papers for novelty and relevance. "
            "Provide objective, data-driven assessments."
        )

        for i in range(0, len(papers), batch_size):
            batch = papers[i : i + batch_size]
            paper_payload = [
                {
                    "id": p.get("id"),
                    "title": p.get("title"),
                    "abstract": p.get("abstract"),
                    "categories": p.get("categories")
                }
                for p in batch
            ]

            prompt = (
                f"Analyze the following research papers. For each paper, return a JSON object with: "
                f"novelty_score (float 0-10), themes (list of 3-5 keywords), "
                f"is_notable (boolean, true if novelty_score >= {self.threshold}), "
                f"and rationale (exactly 1 sentence). "
                f"Return the results as a JSON list of objects in the same order as the input papers. "
                f"Output ONLY the JSON list, no preamble or markdown formatting.\n\n"
                f"Papers:\n{json.dumps(paper_payload)}"
            )

            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4000,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                content = response.content[0].text.strip()
                # Handle potential markdown formatting from API
                if content.startswith("```"):
                    lines = content.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    content = "\n".join(lines).strip()
                
                batch_results = json.loads(content)
                
                if isinstance(batch_results, list):
                    for paper, result in zip(batch, batch_results):
                        # Ensure is_notable follows the specific threshold logic
                        if 'novelty_score' in result:
                            result['is_notable'] = result['novelty_score'] >= self.threshold
                        
                        paper.update(result)
                        analyzed_papers.append(paper)
                else:
                    logger.error(f"Unexpected API response format for batch at index {i}")
            except Exception as e:
                logger.error(f"Failed to analyze batch starting at {i}: {e}")
                continue

        return analyzed_papers

def identify_cross_domain(papers: List[Dict]) -> List[Dict]:
    """
    Returns papers that bridge multiple monitored domains:
    - AI/ML (cs.AI, cs.LG)
    - Quantitative Biology (q-bio)
    - Robotics (cs.RO)
    """
    domain_groups = {
        'AI_ML': {'cs.AI', 'cs.LG'},
        'Q_BIO': {'q-bio'},
        'ROBOTICS': {'cs.RO'}
    }
    
    cross_domain = []
    for paper in papers:
        categories = paper.get('categories', [])
        if isinstance(categories, str):
            categories = [categories]
            
        found_domains = set()
        for cat in categories:
            if any(cat.startswith(target) for target in domain_groups['AI_ML']):
                found_domains.add('AI_ML')
            if cat.startswith('q-bio'):
                found_domains.add('Q_BIO')
            if cat.startswith('cs.RO'):
                found_domains.add('ROBOTICS')
                
        if len(found_domains) >= 2:
            cross_domain.append(paper)
            
    return cross_domain
