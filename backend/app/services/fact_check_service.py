# backend/app/services/fact_check_service.py
import re
import asyncio
import httpx
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..schemas.fact_check import FactCheckItem, ClaimType, Verdict

class FactCheckService:
    def __init__(self):
        self.technical_indicators = {
            "code_snippets": [r"```[\s\S]*?```", r"<code>[\s\S]*?</code>", r"def\s+\w+\s*\([^)]*\):"],
            "version_numbers": [r"\b\d+\.\d+(\.\d+)?\b", r"\bv?\d+(\.\d+)*\b"],
            "api_references": [r"API\s+key", r"endpoint", r"GET|POST|PUT|DELETE", r"status code"],
            "error_messages": [r"error", r"exception", r"failed", r"cannot", r"invalid"],
            "technical_terms": [r"framework", r"library", r"dependency", r"configuration", r"deployment"]
        }
        
        # Enhanced technical knowledge base
        self.technical_knowledge = {
            "eol_versions": {
                "python": {"3.6": "2018-12-23", "3.7": "2023-06-27", "3.8": "2024-10-14"},
                "nodejs": {"12": "2022-04-30", "14": "2023-04-30", "16": "2023-09-11"},
                "react": {"16": "2020-10-20", "17": "2022-03-29"},
                "django": {"2.2": "2022-04-11", "3.1": "2021-04-06", "3.2": "2024-04-01"}
            },
            "common_misconceptions": [
                {
                    "pattern": r"blockchain.*(completely secure|100% safe|unhackable)",
                    "truth": "Blockchain has specific security properties but isn't universally secure against all threats",
                    "severity": "medium"
                },
                {
                    "pattern": r"ai.*(replace|take over).*developer",
                    "truth": "AI augments developer capabilities but doesn't replace human judgment and creativity",
                    "severity": "low"
                },
                {
                    "pattern": r"microservices.*always.*better.*monolith",
                    "truth": "Microservices have trade-offs and aren't always better than monoliths",
                    "severity": "medium"
                },
                {
                    "pattern": r"python.*fastest.*language",
                    "truth": "Python prioritizes readability and productivity over raw execution speed",
                    "severity": "medium"
                }
            ],
            "performance_claims": [
                r"(\d+)x faster",
                r"(\d+)% performance improvement",
                r"benchmark.*shows"
            ]
        }
    
    async def check_content(self, text_content: str) -> List[FactCheckItem]:
        """Perform fact checking on technical content with better filtering"""
        
        # First, check if this is actually technical content
        if not self.is_technical_content(text_content):
            return [FactCheckItem(
                claim="Content screening",
                claim_type=ClaimType.OTHER,
                context="This appears to be non-technical content",
                verdict=Verdict.UNVERIFIED,
                confidence=0.9,
                sources=[],
                explanation="The fact-checker is designed for technical blogs and documentation. Please use content about programming, frameworks, or software development."
            )]
        
        # Extract only meaningful factual claims
        claims = self.extract_claims(text_content)
        
        if not claims:
            return [FactCheckItem(
                claim="No verifiable technical claims found",
                claim_type=ClaimType.OTHER,
                context="The content doesn't contain specific technical claims to verify",
                verdict=Verdict.UNVERIFIED,
                confidence=0.8,
                sources=[],
                explanation="The content appears to be announcements or general information without specific factual claims about versions, performance, or capabilities."
            )]
        
        checked_claims = []
        
        # Process claims in parallel for better performance
        verification_tasks = []
        for claim in claims:
            verification_tasks.append(self.verify_claim_enhanced(claim))
        
        results = await asyncio.gather(*verification_tasks)
        
        for claim, result in zip(claims, results):
            checked_claims.append(FactCheckItem(
                claim=claim["text"],
                claim_type=claim["type"],
                context=claim.get("context", ""),
                verdict=result["verdict"],
                confidence=result["confidence"],
                sources=result.get("sources", []),
                explanation=result["explanation"]
            ))
        
        return checked_claims
    
    def is_technical_content(self, text: str) -> bool:
        """Check if content is actually technical (programming, software, etc.)"""
        technical_keywords = [
            'python', 'javascript', 'java', 'react', 'vue', 'angular', 'node', 
            'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'api', 'database',
            'framework', 'library', 'function', 'class', 'method', 'variable',
            'git', 'github', 'deploy', 'server', 'backend', 'frontend', 'code',
            'programming', 'development', 'software', 'algorithm', 'bug', 'debug',
            'npm', 'package', 'import', 'export', 'component', 'hook', 'state'
        ]
        
        text_lower = text.lower()
        technical_matches = sum(1 for keyword in technical_keywords if keyword in text_lower)
        
        # Consider content technical if it has at least 3 technical keywords
        return technical_matches >= 3
    
    def extract_claims(self, text: str) -> List[Dict[str, Any]]:
        """Ultra-strict claim extraction focusing only on verifiable technical facts"""
        claims = []
        
        # Extract sentences
        sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 25 or len(sentence) > 200:
                continue
                
            # Only extract if it's a verifiable factual claim
            if self.is_verifiable_technical_claim(sentence):
                claim_type = self.classify_claim_type(sentence)
                claims.append({
                    "text": sentence,
                    "type": claim_type,
                    "context": self.get_surrounding_context(text, sentence),
                    "technical_indicators": self.extract_technical_indicators(sentence)
                })
        
        return claims
    
    def is_verifiable_technical_claim(self, text: str) -> bool:
        """ULTRA-STRICT: Only detect claims that can actually be verified"""
        text_lower = text.lower().strip()
        
        # Skip very short or very long sentences
        if len(text) < 25 or len(text) > 200:
            return False
        
        # Skip questions
        if text_lower.startswith(('how', 'what', 'why', 'when', 'where', 'can ', 'is ', 'are ')) and '?' in text:
            return False
        
        # Skip opinion/advice phrases
        opinion_phrases = [
            'we think', 'we believe', 'in our opinion', 'we recommend', 'you should',
            'we suggest', 'it is recommended', 'best practice', 'we hope', 
            'for more information', 'see the', 'check out', 'learn more'
        ]
        if any(phrase in text_lower for phrase in opinion_phrases):
            return False
        
        # Skip announcement phrases
        announcement_phrases = [
            'is now available', 'has been released', 'we are excited', 'announcing',
            'introducing', 'welcome to', 'is here', 'just launched', 'new release',
            'latest version', 'now supports', 'now available'
        ]
        if any(phrase in text_lower for phrase in announcement_phrases):
            return False
        
        # Skip descriptive/narrative phrases
        descriptive_phrases = [
            'the overall', 'the goal is', 'the strategy is', 'this means that',
            'in other words', 'for example', 'as shown', 'as you can see'
        ]
        if any(phrase in text_lower for phrase in descriptive_phrases):
            return False
        
        # MUST HAVE: Specific factual claim patterns
        verifiable_patterns = [
            # Version compatibility
            r"requires.*\d+\.\d+", r"compatible with.*\d+\.\d+", r"supports.*\d+\.\d+",
            # Performance numbers
            r"\d+%.*faster", r"\d+x.*faster", r"\d+.*performance", 
            # Security claims
            r"secure against", r"vulnerability in", r"safe from",
            # Capability claims with numbers
            r"can handle.*\d+", r"supports up to.*\d+", r"capable of.*\d+",
            # Comparative claims
            r"better than.*\d", r"faster than.*\d", r"improves.*\d+",
            # Version status claims
            r"version.*\d+\.\d+.*supported", r"version.*\d+\.\d+.*deprecated",
            r"version.*\d+\.\d+.*end.of.life", r"version.*\d+\.\d+.*eol"
        ]
        
        has_verifiable_pattern = any(re.search(pattern, text_lower) for pattern in verifiable_patterns)
        
        # MUST HAVE: Technical content
        technical_terms = ['python', 'react', 'node', 'javascript', 'java', 'docker', 'kubernetes', 
                          'api', 'database', 'framework', 'library', 'algorithm', 'performance',
                          'security', 'compatible', 'version', 'requires', 'supports']
        has_technical_terms = any(term in text_lower for term in technical_terms)
        
        return has_verifiable_pattern and has_technical_terms
    
    def extract_technical_indicators(self, text: str) -> Dict[str, Any]:
        """Extract technical elements from claim"""
        indicators = {
            "versions": re.findall(r'\b\d+\.\d+(?:\.\d+)?\b', text),
            "technologies": self.detect_technologies(text),
            "numbers": re.findall(r'\b\d+(?:\.\d+)?%?\b', text),
            "comparisons": re.findall(r'\b(faster|slower|better|worse|more|less)\b', text, re.IGNORECASE),
            "absolute_terms": re.findall(r'\b(always|never|every|all|none|completely|100%)\b', text, re.IGNORECASE)
        }
        return indicators
    
    def detect_technologies(self, text: str) -> List[str]:
        """Detect mentioned technologies"""
        technologies = []
        tech_keywords = {
            "python": ["python", "django", "flask"],
            "javascript": ["javascript", "node", "react", "vue", "angular"],
            "java": ["java", "spring"],
            "cloud": ["aws", "azure", "gcp", "docker", "kubernetes"]
        }
        
        text_lower = text.lower()
        for tech, keywords in tech_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                technologies.append(tech)
        
        return technologies
    
    async def verify_claim_enhanced(self, claim: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced claim verification with multiple methods"""
        claim_text = claim["text"]
        claim_type = claim["type"]
        indicators = claim.get("technical_indicators", {})
        
        # Use rule-based verification
        rule_based_result = await self.verify_with_rules(claim_text, claim_type, indicators)
        
        return rule_based_result
    
    async def verify_with_rules(self, claim: str, claim_type: ClaimType, indicators: Dict) -> Dict[str, Any]:
        """Rule-based verification using technical knowledge"""
        if claim_type == ClaimType.VERSION_INFO:
            return await self.verify_version_claim_enhanced(claim, indicators)
        elif claim_type == ClaimType.PERFORMANCE:
            return await self.verify_performance_claim_enhanced(claim, indicators)
        elif claim_type == ClaimType.SECURITY:
            return await self.verify_security_claim_enhanced(claim, indicators)
        elif claim_type == ClaimType.COMPATIBILITY:
            return await self.verify_compatibility_claim_enhanced(claim, indicators)
        else:
            return await self.verify_general_claim(claim, indicators)
    
    async def verify_version_claim_enhanced(self, claim: str, indicators: Dict) -> Dict[str, Any]:
        """Enhanced version claim verification"""
        versions = indicators.get("versions", [])
        technologies = indicators.get("technologies", [])
        
        for tech in technologies:
            for version in versions:
                if tech in self.technical_knowledge["eol_versions"]:
                    if version in self.technical_knowledge["eol_versions"][tech]:
                        return {
                            "verdict": Verdict.FALSE,
                            "confidence": 0.95,
                            "explanation": f"{tech.capitalize()} {version} reached end-of-life on {self.technical_knowledge['eol_versions'][tech][version]} and should not be used in new projects",
                            "sources": [f"Official {tech} documentation"]
                        }
        
        # If we found versions but they're not EOL, consider it true
        if versions and technologies:
            return {
                "verdict": Verdict.TRUE,
                "confidence": 0.85,
                "explanation": "Version information appears to be accurate and up-to-date",
                "sources": []
            }
        
        return {
            "verdict": Verdict.UNVERIFIED,
            "confidence": 0.70,
            "explanation": "Unable to verify version claim with current knowledge base",
            "sources": []
        }
    
    async def verify_performance_claim_enhanced(self, claim: str, indicators: Dict) -> Dict[str, Any]:
        """Verify performance claims"""
        # Check for unrealistic performance numbers
        numbers = indicators.get("numbers", [])
        
        for number in numbers:
            if '%' in number:
                percentage = float(number.replace('%', ''))
                if percentage > 1000:  # Unrealistic improvement
                    return {
                        "verdict": Verdict.FALSE,
                        "confidence": 0.85,
                        "explanation": f"Performance improvement of {percentage}% seems unrealistic without specific benchmark evidence",
                        "sources": []
                    }
            elif 'x' in claim.lower() and any(num.isdigit() for num in numbers):
                # Check for "X times faster" claims
                for num in numbers:
                    if num.isdigit() and int(num) > 100:
                        return {
                            "verdict": Verdict.FALSE,
                            "confidence": 0.80,
                            "explanation": f"{num}x performance improvement claims require substantial evidence and are often exaggerated",
                            "sources": []
                        }
        
        return {
            "verdict": Verdict.UNVERIFIED,
            "confidence": 0.70,
            "explanation": "Performance claims require specific benchmark context and evidence for verification",
            "sources": []
        }
    
    async def verify_security_claim_enhanced(self, claim: str, indicators: Dict) -> Dict[str, Any]:
        """Verify security-related claims"""
        claim_lower = claim.lower()
        
        # Check for absolute security claims
        absolute_terms = ["completely secure", "100% safe", "unhackable", "no vulnerabilities", "immune to"]
        if any(term in claim_lower for term in absolute_terms):
            return {
                "verdict": Verdict.FALSE,
                "confidence": 0.90,
                "explanation": "Absolute security claims are generally inaccurate; all systems have potential vulnerabilities and require ongoing maintenance",
                "sources": ["Security best practices"]
            }
        
        return {
            "verdict": Verdict.UNVERIFIED,
            "confidence": 0.75,
            "explanation": "Security claims require specific threat model context for proper verification",
            "sources": []
        }
    
    async def verify_compatibility_claim_enhanced(self, claim: str, indicators: Dict) -> Dict[str, Any]:
        """Verify compatibility claims"""
        versions = indicators.get("versions", [])
        technologies = indicators.get("technologies", [])
        
        if versions and technologies:
            return {
                "verdict": Verdict.UNVERIFIED,
                "confidence": 0.65,
                "explanation": f"Compatibility between {', '.join(technologies)} versions {', '.join(versions)} requires specific testing documentation",
                "sources": []
            }
        
        return {
            "verdict": Verdict.UNVERIFIED,
            "confidence": 0.60,
            "explanation": "Compatibility claims require specific version testing for verification",
            "sources": []
        }
    
    async def verify_general_claim(self, claim: str, indicators: Dict) -> Dict[str, Any]:
        """Verify general technical claims"""
        # Check against common misconceptions
        for misconception in self.technical_knowledge["common_misconceptions"]:
            if re.search(misconception["pattern"], claim, re.IGNORECASE):
                return {
                    "verdict": Verdict.FALSE,
                    "confidence": 0.85,
                    "explanation": f"This appears to be a common misconception. {misconception['truth']}",
                    "sources": ["Technical best practices"]
                }
        
        return {
            "verdict": Verdict.UNVERIFIED,
            "confidence": 0.60,
            "explanation": "Unable to verify with current technical knowledge base",
            "sources": []
        }
    
    def classify_claim_type(self, text: str) -> ClaimType:
        """Enhanced claim type classification"""
        text_lower = text.lower()
        
        # Check for version claims
        if re.search(r"\b(version|v)\s*\d+\.\d+", text_lower) or re.search(r"\b\d+\.\d+(\.\d+)?\b", text_lower):
            return ClaimType.VERSION_INFO
        
        # Check for performance claims
        if any(term in text_lower for term in ["faster", "slower", "performance", "benchmark", "speed", "efficient"]):
            return ClaimType.PERFORMANCE
        
        # Check for compatibility claims
        if any(term in text_lower for term in ["compatible", "requires", "works with", "supports", "dependency"]):
            return ClaimType.COMPATIBILITY
        
        # Check for security claims
        if any(term in text_lower for term in ["secure", "vulnerability", "safe", "protection", "encryption"]):
            return ClaimType.SECURITY
        
        # Check for API claims
        if any(re.search(pattern, text_lower) for pattern in self.technical_indicators["api_references"]):
            return ClaimType.API_REFERENCE
        
        # Check for code examples
        if any(re.search(pattern, text_lower) for pattern in self.technical_indicators["code_snippets"]):
            return ClaimType.CODE_EXAMPLE
        
        return ClaimType.OTHER
    
    def get_surrounding_context(self, full_text: str, sentence: str) -> str:
        """Extract context around a claim"""
        index = full_text.find(sentence)
        if index == -1:
            return ""
        
        start = max(0, index - 100)
        end = min(len(full_text), index + len(sentence) + 100)
        return full_text[start:end]