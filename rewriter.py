import os
import json
import random
import string
import time
import re
from typing import List, Dict, Optional, Tuple
import logging

import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.stem import SnowballStemmer
from nltk.corpus import wordnet

# spaCy imports with fallback
try:
    import spacy
    from textblob import TextBlob
    ADVANCED_NLP_AVAILABLE = True
except ImportError:
    ADVANCED_NLP_AVAILABLE = False
    logging.warning("spaCy/TextBlob not available. Install with: pip install spacy textblob")

# Download required NLTK data with better error handling
def download_nltk_data():
    required_nltk_data = [
        ('punkt', 'tokenizers/punkt'),
        ('punkt_tab', 'tokenizers/punkt_tab'), 
        ('wordnet', 'corpora/wordnet'),
        ('averaged_perceptron_tagger', 'taggers/averaged_perceptron_tagger'),
        ('omw-1.4', 'corpora/omw-1.4')
    ]
    
    for data_package, path in required_nltk_data:
        try:
            nltk.data.find(path)
        except LookupError:
            print(f"Downloading {data_package}...")
            try:
                nltk.download(data_package, quiet=True)
            except Exception as e:
                print(f"Error downloading {data_package}: {e}")
                # Try alternative approach
                if data_package == 'punkt_tab':
                    try:
                        nltk.download('punkt', quiet=True)
                    except:
                        pass
        except Exception as e:
            print(f"Error with {data_package}: {e}")
            try:
                nltk.download(data_package, quiet=True)
            except:
                pass

# Call the function
download_nltk_data()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize stemmer
stemmer = SnowballStemmer('english')

class LocalRefinementRepository:
    """Advanced local text refinement using spaCy, TextBlob, and NLTK"""
    
    def __init__(self):
        self.nlp = None
        self.advanced_features = ADVANCED_NLP_AVAILABLE
        
        if self.advanced_features:
            try:
                # Try to load spaCy model
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("Loaded spaCy model for advanced text processing")
            except OSError:
                logger.warning("spaCy model 'en_core_web_sm' not found. Install with: python -m spacy download en_core_web_sm")
                self.advanced_features = False
        
        if not self.advanced_features:
            logger.info("Using NLTK-based text refinement")
    
    def refine_text(self, text: str) -> Tuple[str, Optional[str]]:
        """Refine text using best available local NLP tools"""
        try:
            if self.advanced_features and self.nlp:
                return self._advanced_refinement(text), None
            else:
                return self._nltk_refinement(text), None
                
        except Exception as e:
            logger.error(f"Error in text refinement: {str(e)}")
            return self._basic_refinement(text), None
    
    def _advanced_refinement(self, text: str) -> str:
        """Advanced refinement using spaCy and TextBlob"""
        try:
            # Grammar correction with TextBlob
            blob = TextBlob(text)
            corrected_text = str(blob.correct())
            
            # Process with spaCy
            doc = self.nlp(corrected_text)
            sentences = [sent.text.strip() for sent in doc.sents]
            
            refined_sentences = []
            for sentence in sentences:
                refined = self._improve_sentence_advanced(sentence)
                refined_sentences.append(refined)
            
            return " ".join(refined_sentences)
            
        except Exception as e:
            logger.warning(f"Advanced refinement failed, falling back to NLTK: {str(e)}")
            return self._nltk_refinement(text)
    
    def _improve_sentence_advanced(self, sentence: str) -> str:
        """Improve sentence using advanced NLP with academic tone"""
        if not sentence.strip():
            return sentence
        
        # Ensure proper capitalization
        sentence = sentence.strip()
        if sentence:
            sentence = sentence[0].upper() + sentence[1:]
        
        # Academic-appropriate transition words
        transition_words = {
            "Also": ["Furthermore", "Additionally", "Moreover", "In addition"],
            "But": ["However", "Nevertheless", "Nonetheless", "Conversely"],
            "So": ["Therefore", "Consequently", "Thus", "Hence"],
            "And": ["Furthermore", "Additionally", "Moreover"],
            "First": ["Initially", "Primarily", "To begin with"],
            "Finally": ["In conclusion", "Ultimately", "Lastly"]
        }
        
        for original, alternatives in transition_words.items():
            if sentence.startswith(original + " ") and random.random() < 0.25:
                replacement = random.choice(alternatives)
                sentence = sentence.replace(original, replacement, 1)
                break
        
        return sentence
    
    def _nltk_refinement(self, text: str) -> str:
        """Refinement using NLTK"""
        try:
            sentences = sent_tokenize(text)
            refined_sentences = []
            
            for sentence in sentences:
                refined = self._improve_sentence_nltk(sentence)
                refined_sentences.append(refined)
            
            return " ".join(refined_sentences)
            
        except Exception as e:
            logger.warning(f"NLTK refinement failed, using basic refinement: {str(e)}")
            return self._basic_refinement(text)
    
    def _improve_sentence_nltk(self, sentence: str) -> str:
        """Improve sentence using NLTK"""
        if not sentence.strip():
            return sentence
        
        # Basic improvements
        sentence = sentence.strip()
        if sentence:
            sentence = sentence[0].upper() + sentence[1:]
        
        # Word-level improvements using WordNet
        words = word_tokenize(sentence)
        improved_words = []
        
        for word in words:
            if word.isalpha() and len(word) > 4 and random.random() < 0.1:
                synonym = self._get_wordnet_synonym(word)
                if synonym and synonym != word.lower():
                    # Preserve original capitalization
                    if word[0].isupper():
                        synonym = synonym.capitalize()
                    improved_words.append(synonym)
                else:
                    improved_words.append(word)
            else:
                improved_words.append(word)
        
        # Reconstruct sentence with proper spacing using NLTK's detokenizer approach
        from nltk.tokenize.treebank import TreebankWordDetokenizer
        detokenizer = TreebankWordDetokenizer()
        return detokenizer.detokenize(improved_words)
    
    def _get_wordnet_synonym(self, word: str) -> Optional[str]:
        """Get synonym from WordNet"""
        try:
            synsets = wordnet.synsets(word.lower())
            if synsets:
                synonyms = []
                for syn in synsets[:2]:  # Check first 2 synsets
                    for lemma in syn.lemmas():
                        synonym = lemma.name().replace('_', ' ')
                        if (synonym != word.lower() and 
                            len(synonym.split()) == 1 and  # Single word only
                            synonym.isalpha()):
                            synonyms.append(synonym)
                
                if synonyms:
                    return random.choice(synonyms)
            return None
        except Exception:
            return None
    
    def _basic_refinement(self, text: str) -> str:
        """Basic text refinement without external libraries"""
        # Clean up text
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Fix common formatting issues - MORE COMPREHENSIVE
        replacements = {
            r'[\s\r\n]+([,.!?;:])': r'\1',  # Remove space before punctuation
            r'([.!?])\s*([a-z])': r'\1 \2',  # Ensure space after sentence endings
            r'\bi\b': 'I',  # Capitalize standalone 'i'
            r'\s+([)\]}])': r'\1',  # Remove space before closing brackets
            r'([(\[{])\s+': r'\1',  # Remove space after opening brackets
            r'\s{2,}': ' ',  # Replace multiple spaces with single space
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)
        
        # Ensure sentences start with capital letters
        sentences = re.split(r'([.!?]+)', text)
        result = []
        
        for i, part in enumerate(sentences):
            if i % 2 == 0 and part.strip():  # Sentence content
                part = part.strip()
                if part:
                    part = part[0].upper() + part[1:]
                result.append(part)
            else:  # Punctuation
                result.append(part)
        
        # Join and apply final cleanup passes
        final_text = ''.join(result)
        
        # Multiple cleanup passes to ensure all spacing issues are fixed
        final_text = re.sub(r'\s+([,.!?;:])', r'\1', final_text)  # Remove spaces before punctuation
        # Apply multiple passes to ensure no spaces are left before punctuation
        for _ in range(2):  # Multiple passes to catch nested cases
            final_text = re.sub(r'\s+([,.!?;:])', r'\1', final_text)
        final_text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', final_text)  # Ensure space after sentence endings
        final_text = re.sub(r'\s{2,}', ' ', final_text)  # Replace multiple spaces with single space
        final_text = re.sub(r'\s+$', '', final_text)  # Remove trailing spaces
        final_text = re.sub(r'^\s+', '', final_text)  # Remove leading spaces
        
        return final_text

class LocalSynonymRepository:
    """Enhanced local synonym repository using NLTK WordNet"""
    
    def __init__(self):
        # Ensure WordNet is available
        try:
            nltk.data.find('corpora/wordnet')
        except LookupError:
            nltk.download('wordnet', quiet=True)
            nltk.download('omw-1.4', quiet=True)
    
    def get_synonym(self, word: str) -> Tuple[str, Optional[str]]:
        """Get synonym for a word using WordNet"""
        try:
            clean_word = word.lower().strip()
            if len(clean_word) < 3:
                return "", "Word too short for synonym replacement"
            
            synsets = wordnet.synsets(clean_word)
            if not synsets:
                return "", "No synonyms found for the word"
            
            # Collect synonyms from multiple synsets
            all_synonyms = []
            for synset in synsets[:3]:  # Check first 3 synsets
                for lemma in synset.lemmas():
                    synonym = lemma.name().replace('_', ' ')
                    if (synonym != clean_word and 
                        len(synonym.split()) == 1 and  # Single word only
                        synonym.isalpha() and
                        len(synonym) >= 3):
                        all_synonyms.append(synonym)
            
            if not all_synonyms:
                return "", "No suitable synonyms found"
            
            # Filter by similarity (prefer words of similar length)
            word_len = len(clean_word)
            filtered_synonyms = [
                syn for syn in all_synonyms 
                if abs(len(syn) - word_len) <= 3
            ]
            
            if filtered_synonyms:
                return random.choice(filtered_synonyms), None
            elif all_synonyms:
                return random.choice(all_synonyms), None
            else:
                return "", "No valid synonyms found"
                
        except Exception as e:
            return "", f"Error fetching synonym: {str(e)}"

class TextRewriteService:
    """Enhanced service for rewriting and humanizing text"""
    
    def __init__(self):
        self.refinement_repo = LocalRefinementRepository()
        self.synonym_repo = LocalSynonymRepository()
        self.filler_sentences = self._load_fillers()
        random.seed(time.time())
        logger.info("TextRewriteService initialized with local refinement")
    
    def rewrite_text(self, text: str) -> Tuple[str, Optional[str]]:
        """Main rewriting function using local refinement"""
        try:
            # Apply local refinement
            refined, err = self.refinement_repo.refine_text(text)
            return refined if refined else text, err
        except Exception as e:
            logger.error(f"Error in text rewriting: {str(e)}")
            return text, f"Rewriting error: {str(e)}"
    
    def rewrite_text_with_modifications(self, text: str) -> Tuple[str, Optional[str]]:
        """Enhanced rewriting with comprehensive modifications"""
        try:
            # Start with base rewriting
            base_result, err = self.rewrite_text(text)
            if err:
                return text, err
            
            # Apply additional enhancements with HIGHER probability
            sentences = self._split_sentences(base_result)
            transformed = []
            
            for sentence in sentences:
                # Apply various transformations with INCREASED probability
                if random.random() < 0.8:  # Increased from 0.4
                    sentence = self._vary_sentence_structure(sentence)
                if random.random() < 0.6:  # Increased from 0.2
                    sentence = self._replace_synonyms(sentence)
                if random.random() < 0.5:  # Increased from 0.15
                    sentence = self._add_natural_noise(sentence)
                
                transformed.append(sentence)
            
            # More aggressive sentence reordering
            if len(transformed) > 2 and random.random() < 0.4:  # Increased from 0.2
                if len(transformed) > 3:
                    middle = transformed[1:-1]
                    random.shuffle(middle)
                    transformed = [transformed[0]] + middle + [transformed[-1]]
            
            # More frequent contextual filler addition
            if len(transformed) > 1 and random.random() < 0.4:  # Increased from 0.2
                filler = self._get_contextual_filler(transformed)
                if filler:
                    # Insert at random position (not just end)
                    insert_pos = random.randint(1, len(transformed))
                    transformed.insert(insert_pos, filler)
            
            return " ".join(transformed), None
            
        except Exception as e:
            logger.error(f"Error in enhanced rewriting: {str(e)}")
            return text, f"Enhanced rewriting error: {str(e)}"
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences using NLTK"""
        try:
            return [s.strip() for s in sent_tokenize(text) if s.strip()]
        except Exception:
            return [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    
    def _vary_sentence_structure(self, sentence: str) -> str:
        """Intelligently vary sentence structure"""
        if len(sentence.split()) < 4:
            return sentence
        
        transformations = [
            self._add_transition_word,
            self._rearrange_clauses,
            self._convert_contractions,
        ]
        
        transformation = random.choice(transformations)
        return transformation(sentence)
    
    def _add_transition_word(self, sentence: str) -> str:
        """Add academic transition words to sentences"""
        transitions = [
            "Furthermore, ", "Additionally, ", "Moreover, ", "Notably, ",
            "Significantly, ", "Importantly, ", "Specifically, ", "Indeed, ",
            "Particularly, ", "Evidently, ", "Consequently, ", "Subsequently, ",
            "Interestingly, ", "Remarkably, ", "Essentially, ", "Ultimately, ",
            "Clearly, ", "Obviously, ", "Undoubtedly, ", "Certainly, "
        ]
        
        if not sentence[0].isupper():
            return sentence
        
        # Increased probability from 0.2 to 0.5
        if random.random() < 0.5:
            transition = random.choice(transitions)
            return transition + sentence.lower()
        
        return sentence
    
    def _rearrange_clauses(self, sentence: str) -> str:
        """Simple clause rearrangement"""
        if ', ' in sentence and sentence.count(',') == 1:
            parts = sentence.split(', ', 1)
            if len(parts) == 2 and random.random() < 0.3:
                part1, part2 = parts
                return f"{part2}, {part1.lower()}"
        
        return sentence
    
    def _convert_contractions(self, sentence: str) -> str:
        """Expand contractions for academic formality"""
        contractions = {
            "don't": "do not", "won't": "will not", "can't": "cannot",
            "isn't": "is not", "aren't": "are not", "wasn't": "was not",
            "weren't": "were not", "hasn't": "has not", "haven't": "have not",
            "wouldn't": "would not", "couldn't": "could not", "shouldn't": "should not",
            "it's": "it is", "that's": "that is", "there's": "there is",
            "what's": "what is", "you're": "you are", "we're": "we are",
            "they're": "they are"
        }
        
        # Always expand contractions for academic tone (increased probability)
        if random.random() < 0.8:
            for contraction, expansion in contractions.items():
                if contraction in sentence.lower():
                    # Case-sensitive replacement
                    sentence = re.sub(re.escape(contraction), expansion, sentence, flags=re.IGNORECASE)
                    break
        
        return sentence
    
    def _replace_synonyms(self, sentence: str) -> str:
        """Intelligently replace words with synonyms - MORE AGGRESSIVE"""
        words = sentence.split()
        modifications = 0
        max_modifications = max(1, len(words) // 4)  # Allow more modifications
        
        for i, word in enumerate(words):
            if modifications >= max_modifications:
                break
                
            # Extract clean word
            clean_word = re.sub(r'[^\w]', '', word).lower()
            
            # Skip if too short or too common
            if (len(clean_word) < 3 or  # Reduced from 4 to 3
                self._is_common_word(clean_word)):
                continue
            
            # INCREASED probability from 0.15 to 0.4
            if random.random() < 0.4:
                synonym, err = self.synonym_repo.get_synonym(clean_word)
                if not err and synonym:
                    # Preserve original word formatting
                    new_word = self._preserve_word_format(word, synonym)
                    words[i] = new_word
                    modifications += 1
        
        return " ".join(words)
    
    def _preserve_word_format(self, original: str, replacement: str) -> str:
        """Preserve capitalization and punctuation of original word"""
        # Extract prefix and suffix punctuation
        prefix = ""
        suffix = ""
        core_word = original
        
        # Get leading punctuation
        start = 0
        while start < len(original) and not original[start].isalpha():
            prefix += original[start]
            start += 1
        
        # Get trailing punctuation
        end = len(original) - 1
        while end >= 0 and not original[end].isalpha():
            suffix = original[end] + suffix
            end -= 1
        
        if start <= end:
            core_word = original[start:end+1]
        
        # Apply capitalization pattern
        if core_word and core_word[0].isupper():
            replacement = replacement.capitalize()
        elif core_word.isupper():
            replacement = replacement.upper()
        elif core_word.islower():
            replacement = replacement.lower()
        
        return prefix + replacement + suffix
    
    def _add_natural_noise(self, sentence: str) -> str:
        """Add natural linguistic variations - MORE AGGRESSIVE"""
        # More comprehensive academic-appropriate replacements
        replacements = {
            " and ": [" as well as ", " along with ", " in addition to ", " together with "],
            " but ": [" however, ", " nevertheless, ", " nonetheless, ", " conversely, "],
            " because ": [" due to the fact that ", " given that ", " since ", " as "],
            " so ": [" therefore, ", " consequently, ", " thus, ", " hence, "],
            " also ": [" furthermore, ", " additionally, ", " moreover, ", " likewise, "],
            " use ": [" utilize ", " employ ", " implement ", " apply "],
            " show ": [" demonstrate ", " illustrate ", " reveal ", " display "],
            " help ": [" facilitate ", " assist ", " aid ", " support "],
            " get ": [" obtain ", " acquire ", " achieve ", " secure "],
            " make ": [" create ", " establish ", " generate ", " produce "],
            " find ": [" discover ", " identify ", " determine ", " locate "],
            " think ": [" consider ", " believe ", " suggest ", " propose "],
            " very ": [" significantly ", " considerably ", " substantially ", " remarkably "],
            " big ": [" substantial ", " significant ", " considerable ", " extensive "],
            " small ": [" minimal ", " limited ", " modest ", " slight "],
            " good ": [" excellent ", " effective ", " beneficial ", " advantageous "],
            " bad ": [" detrimental ", " problematic ", " unfavorable ", " adverse "],
            " new ": [" novel ", " innovative ", " contemporary ", " recent "],
            " old ": [" traditional ", " established ", " conventional ", " previous "],
            " many ": [" numerous ", " multiple ", " various ", " several "],
            " few ": [" limited ", " minimal ", " sparse ", " scarce "]
        }
        
        # Apply multiple replacements per sentence with higher probability
        replacements_made = 0
        max_replacements = 3  # Allow up to 3 replacements per sentence
        
        for old, new_options in replacements.items():
            if replacements_made >= max_replacements:
                break
                
            if old in sentence.lower() and random.random() < 0.3:  # Increased from 0.15
                new_phrase = random.choice(new_options)
                # Case-sensitive replacement
                sentence = re.sub(re.escape(old), new_phrase, sentence, count=1, flags=re.IGNORECASE)
                replacements_made += 1
        
        return sentence
    
    def _get_contextual_filler(self, sentences: List[str]) -> str:
        """Generate academic contextual filler sentence"""
        if not sentences:
            return ""
        
        # Extract themes from the text
        all_text = " ".join(sentences)
        keywords = self._extract_keywords(all_text)
        
        if keywords and len(keywords) > 0:
            # Academic templates
            templates = [
                "This analysis underscores the significance of {keyword}.",
                "The examination of {keyword} reveals important insights.",
                "Such findings regarding {keyword} warrant further consideration.",
                "The implications of {keyword} are particularly noteworthy.",
                "This investigation into {keyword} provides valuable understanding.",
                "The study of {keyword} demonstrates considerable importance.",
                "These observations concerning {keyword} merit attention."
            ]
            
            template = random.choice(templates)
            keyword = random.choice(keywords[:3])  # Use top 3 keywords
            return template.format(keyword=keyword)
        
        # Fallback to academic transitions
        return random.choice(self.filler_sentences)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text"""
        # Simple keyword extraction
        words = re.findall(r'\b[a-zA-Z]{5,}\b', text.lower())
        
        # Filter out common words
        filtered_words = [
            word for word in words 
            if not self._is_common_word(word)
        ]
        
        # Return unique keywords
        return list(dict.fromkeys(filtered_words))
    
    def _is_common_word(self, word: str) -> bool:
        """Check if word is too common for replacement in academic context"""
        # Expanded list including academic terms to preserve
        common_words = {
            "the", "and", "that", "this", "with", "have", "will", "been", 
            "from", "they", "know", "want", "been", "good", "much", "some",
            "time", "very", "when", "come", "here", "just", "like", "long",
            "make", "many", "over", "such", "take", "than", "them", "well",
            "were", "work", "about", "could", "would", "there", "their",
            "which", "should", "think", "where", "through", "because",
            "between", "important", "different", "following", "around",
            "though", "without", "another", "example", "however", "therefore",
            # Academic terms to preserve
            "research", "study", "analysis", "data", "method", "result",
            "conclusion", "evidence", "theory", "hypothesis", "findings",
            "literature", "methodology", "framework", "approach", "concept",
            "significant", "substantial", "considerable", "demonstrate",
            "indicate", "suggest", "reveal", "establish", "examine", "AI", "IoT", "ML", "NLP", 
            "deep learning", "blockchain", "cloud computing", "big data", "cybersecurity", "data science", 
            "augmented reality", "virtual reality", "edge computing", "quantum computing", "natural language processing",
            "machine learning", "artificial intelligence", "internet of things", "data analytics", "digital transformation",
            "automation", "smart technology", "sustainability", "innovation", "disruption", "technology"
        }
        return word.lower() in common_words
    
    def _load_fillers(self) -> List[str]:
        """Load academic-appropriate filler sentences"""
        return [
            "This analysis provides valuable insights into the subject matter.",
            "Such examination proves particularly enlightening for understanding the topic.", 
            "These considerations merit further scholarly attention.",
            "The implications of this research become increasingly evident.",
            "This methodological approach yields meaningful academic results.",
            "The findings contribute significantly to the existing body of knowledge.",
            "This investigation enhances our understanding of the phenomenon.",
            "The research demonstrates the complexity of the underlying issues."
        ]

# Public functions for external use
def rewrite_text(text: str, enhanced: bool = False) -> Tuple[str, Optional[str]]:
    """
    Main function to rewrite text
    
    Args:
        text: Input text to rewrite
        enhanced: Whether to use enhanced modifications
        
    Returns:
        Tuple of (rewritten_text, error_message)
    """
    service = TextRewriteService()
    if enhanced:
        return service.rewrite_text_with_modifications(text)
    else:
        return service.rewrite_text(text)

def get_synonym(word: str) -> Tuple[str, Optional[str]]:
    """
    Get synonym for a word
    
    Args:
        word: Word to find synonym for
        
    Returns:
        Tuple of (synonym, error_message)
    """
    repo = LocalSynonymRepository()
    return repo.get_synonym(word)

def refine_text(text: str) -> Tuple[str, Optional[str]]:
    """
    Refine text using NLP tools
    
    Args:
        text: Text to refine
        
    Returns:
        Tuple of (refined_text, error_message)
    """
    repo = LocalRefinementRepository()
    return repo.refine_text(text)